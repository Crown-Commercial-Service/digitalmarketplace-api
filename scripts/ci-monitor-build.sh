#!/bin/bash

failure(){
  echo "ERROR - \$$1 not set"
  exit 1
}

echo "Validate required environment variables"
test $AWS_ACCOUNT_ID        || failure AWS_ACCOUNT_ID
test $AWS_REGION            || failure AWS_REGION
test $AWS_ACCESS_KEY_ID     || failure AWS_ACCESS_KEY_ID
test $AWS_SECRET_ACCESS_KEY || failure AWS_SECRET_ACCESS_KEY
test $DOCKERFILE_PATH       || failure DOCKERFILE_PATH
test $DOCKER_IMAGE_NAME     || failure DOCKER_IMAGE_NAME
test -f $DOCKERFILE_PATH    || failure DOCKERFILE_PATH
echo "All environment variables are supplied"

set -e

GIT_REF=$(git show-ref -s refs/remotes/origin/HEAD)
# aws ecr get-login --region $AWS_REGION
eval $(aws ecr get-login --region $AWS_REGION)

echo "Checking ECR for $DOCKER_IMAGE_NAME registry"
if [[ ! `aws ecr describe-repositories --region $AWS_REGION --query 'repositories[*].{reponame:repositoryName}' --output text | grep ^ausdtomonitoring-${DOCKER_IMAGE_NAME}$` ]]; then
  echo "Docker ECR for ausdtomonitoring-${DOCKER_IMAGE_NAME} does not exist.  Creating"
  aws ecr create-repository --repository-name ausdtomonitoring-$DOCKER_IMAGE_NAME --region $AWS_REGION
fi

echo "Building $DOCKER_IMAGE_NAME"
docker build -t ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ausdtomonitoring-${DOCKER_IMAGE_NAME}:${GIT_REF} $(dirname $DOCKERFILE_PATH)
echo "Pushing Docker image $DOCKER_IMAGE_NAME"
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ausdtomonitoring-${DOCKER_IMAGE_NAME}:${GIT_REF}
