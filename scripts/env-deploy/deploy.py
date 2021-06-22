import fire
import json
from sultan.api import Sultan
import os.path


TEMP_PATH = "temp/"


class EnvDeploy:
    def down(self, name, skip_db=False):
        self.app(name, True)
        self.ups_service(name, True)
        if skip_db is False:
            self.execute_db_task(name=name, delete=True)
            self.postgres_service(name, True)

    def up(self, name, db_name="digitalmarketplace", skip_db=False):
        if skip_db is False:
            self.postgres_service(name)
            self.execute_db_task(name, db_name)
        self.generate_config_files(name)
        self.ups_service(name)
        self.generate_manifest_files(name)
        self.app(name)

    def stop(self, name):
        with Sultan.load() as s:
            app_names = self.__get_app_names(name)
            for k, v in app_names.iteritems():
                self.__print_result(s.cf("stop", v).run())

    def start(self, name):
        with Sultan.load() as s:
            app_names = self.__get_app_names(name)
            for k, v in app_names.iteritems():
                self.__print_result(s.cf("start", v).run())

    def ups_secret_service(self, secret_file, delete=False):
        with Sultan.load() as s:
            if delete is True:
                self.__print_result(s.echo("y").pipe().cf("delete-service", "ups-secret-service").run())
            else:
                self.__print_result(
                    s.cf("create-user-provided-service",
                         "ups-secret-service",
                         "-p {}".format(secret_file))
                     .run())

    def ups_service(self, name, delete=False):
        ups_service_names = self.__get_ups_service_names(name)
        with Sultan.load() as s:
            common_config_name = self.__get_common_config(name)
            if delete is True:
                self.__print_result(s.echo("y").pipe().cf("delete-service", common_config_name).run())
                for k, v in ups_service_names.iteritems():
                    self.__print_result(s.echo("y").pipe().cf("delete-service", v).run())
            else:
                self.__print_result(
                    s.cf("create-user-provided-service",
                         common_config_name,
                         "-p {}{}.json".format(TEMP_PATH, common_config_name))
                     .run())
                for k, v in ups_service_names.iteritems():
                    file = "{}{}.json".format(TEMP_PATH, v)
                    if os.path.exists(file):
                        self.__print_result(
                            s.cf("create-user-provided-service", v, "-p {}".format(file)).run())
                    else:
                        print("Cannot find '{}'. Execute python generate_config_files {} first".format(file, name))

    def postgres_service(self, name, delete=False):
        postgres_service_name = self.__get_postgres_service_name(name)
        with Sultan.load() as s:
            if delete is True:
                self.__print_result(s.echo("y").pipe().cf("delete-service", postgres_service_name).run())
            else:
                self.__print_result(s.cf("create-service", "postgres", "shared", postgres_service_name).run())
                self.__print_result(s.cf("update-service", postgres_service_name, "-c '{\"extensions\":[\"pg_trgm\"]}'").run())

    def app(self, name, delete=False):
        app_names = self.__get_app_names(name)
        app_configs = self.__get_app_config(name)
        api_path = app_configs["api"]["path"]
        if delete is True:
            with Sultan.load() as s:
                for k, v in app_names.iteritems():
                    self.__print_result(s.echo("y").pipe().cf("delete", v, "-r").run())
        else:
            with Sultan.load() as s:
                apps_len = len(app_names)
                i = 1
                s.cd("../../../").and_()
                for k, v in app_names.iteritems():
                    s.cd("{}".format(app_configs[k]["path"])).and_()
                    path = "../../../{}".format(app_configs[k]["path"])
                    file = "../{}/scripts/env-deploy/{}{}.yml".format(api_path, TEMP_PATH, v)
                    if os.path.exists("{}/{}".format(path, file)):
                        npm_commands = app_configs[k]["npm"]
                        for npm_command in npm_commands:
                            s.npm(npm_command).and_()
                        s.cf("zero-downtime-push", v, "-show-app-log", "-f {}".format(file)).and_()
                    else:
                        print("Cannot find '{}'. Execute python generate_manifest_files {} first".format(file, name))
                    
                    i += 1
                    if i <= apps_len:
                        s.cd("..").and_()
                    else:
                        s.cd("..")

            self.__print_result(s.run())

    def generate_config_files(self, name):
        common_config_name = self.__get_common_config(name)
        env_name = self.__get_env_name(name)

        common_config_template = None
        with open("templates/common-config.json.tpl", "r") as file:
            common_config_template = file.read()
            common_config_template = common_config_template.format(env_name=env_name)
        with open("{}{}.json".format(TEMP_PATH, common_config_name), "w") as file:
            file.write(common_config_template)

        ups_service_names = self.__get_ups_service_names(name)
        for k, v in ups_service_names.iteritems():
            config_template = None
            with open("templates/{}-config.json.tpl".format(k), "r") as file:
                config_template = file.read()
                config_template = config_template.format(env_name=env_name)

            with open("{}{}.json".format(TEMP_PATH, v), "w") as file:
                file.write(config_template)

    def generate_manifest_files(self, name):
        app_names = self.__get_app_names(name)
        env_name = self.__get_env_name(name)

        for k, v in app_names.iteritems():
            self.generate_manifest_file(name, env_name, k)

    def generate_manifest_file(self, name, env_name, app_name):
        app_names = self.__get_app_names(name)
        ups_service_names = self.__get_ups_service_names(name)
        common_config_name = self.__get_common_config(name)
        postgres_service_name = self.__get_postgres_service_name(name)

        manifest_template = None
        with open("templates/{}-manifest.yml.tpl".format(app_name), "r") as file:
            manifest_template = file.read()
            manifest_template = manifest_template.format(env_name=env_name,
                                                         common_config_name=common_config_name,
                                                         postgres_service_name=postgres_service_name,
                                                         api_name=app_names["api"],
                                                         api_config_name=ups_service_names["api"],
                                                         buyer_name=app_names["buyer"],
                                                         buyer_config_name=ups_service_names["buyer"],
                                                         supplier_name=app_names["supplier"],
                                                         supplier_config_name=ups_service_names["supplier"],
                                                         frontend_name=app_names["frontend"],
                                                         frontend_config_name=ups_service_names["frontend"],
                                                         admin_name=app_names["admin"],
                                                         admin_config_name=ups_service_names["admin"])
        with open("{}dm-{}-{}.yml".format(TEMP_PATH, name, app_name), "w") as file:
            file.write(manifest_template)

    def execute_db_task(self, name, db_name="digitalmarketplace", snapshot_file="snapshot.tar", delete=False):
        env_name = self.__get_env_name(name)
        db_task_name = "{}-db-task".format(env_name)
        if delete is True:
            print("deleting {}".format(db_task_name))
            with Sultan.load() as s:
                self.__print_result(s.echo("y").pipe().cf("delete", db_task_name).run())
            return

        self.generate_manifest_file(name, env_name, "db-task")

        with Sultan.load(cwd="schema-sync") as s:
            self.__print_result(
                s.pg_dump("--no-owner",
                          "--no-privileges",
                          "--column-inserts",
                          "--dbname={}".format(db_name),
                          "-f snapshot.tar", "-F t").run())

            self.__print_result(
                s.cf("push",
                     db_task_name,
                     "-f ../{}{}.yml".format(TEMP_PATH, db_task_name)).run())

        with Sultan.load() as s:
            result = s.cf("app", db_task_name, "--guid").run()
            self.__print_result(result)
            db_task_id = result.stdout[0]

            db_task_env_file_name = "{}db-task-env.json".format(TEMP_PATH)
            result = s.cf("curl", '"/v2/apps/{}/env"'.format(db_task_id)).redirect(
                db_task_env_file_name,
                append=False,
                stdout=True,
                stderr=False).run()
            self.__print_result(result)

            with open(db_task_env_file_name) as data_file:
                db_task_env = json.load(data_file)

            postgres_uri = db_task_env["system_env_json"]["VCAP_SERVICES"]["postgres"][0]["credentials"]["uri"]
            print(postgres_uri)

            result = s.cf("run-and-wait",
                          db_task_name,
                          '"pgutils/pg_restore --no-owner --dbname={postgres_uri} {snapshot_file}"'
                          .format(postgres_uri=postgres_uri,
                                  snapshot_file=snapshot_file)).run()
            self.__print_result(result)

            self.__print_result(s.cf("stop", db_task_name).run())

    def __print_result(self, result):
        print("stdout")
        for i in result.stdout:
            print(i)

        print("stderr")
        for i in result.stderr:
            print(i)

        print("return code")
        print(result.rc)

    def __get_app_names(self, name):
        env_name = self.__get_env_name(name)
        apps = self.__get_app_config(name)
        result = {}
        for k, v in apps.iteritems():
            result[k] = "{}-{}".format(env_name, k)
        return result

    def __get_ups_service_names(self, name):
        env_name = "ups-dm-{}".format(name)
        apps = self.__get_app_config(name)
        result = {}
        for k, v in apps.iteritems():
            result[k] = "{}-{}".format(env_name, k)
        return result

    def __get_env_name(self, name):
        return "dm-{}".format(name)

    def __get_postgres_service_name(self, name):
        env_name = self.__get_env_name(name)
        return "marketplace-{}-shared".format(env_name)

    def __get_common_config(self, name):
        env_name = self.__get_env_name(name)
        common_config_name = "ups-{}-common".format(env_name)
        return common_config_name

    def __get_app_config(self, name):
        app_config = None
        with open("app_config.json") as app_config_file:
            app_config = json.load(app_config_file)
        return app_config


if __name__ == '__main__':
    fire.Fire(EnvDeploy)
