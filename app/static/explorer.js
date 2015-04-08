function do_i_work() {
    console.log("yes i do");
}

//if enter key is clicked and input fields are not empty, click event is triggered on first visible button
function enter_key_clicks_first_visible_button_if_inputs_not_empty() {
    $(document).keyup(function (e) {
        //if 'enter' key is pressed'
        if (e.keyCode == 13) {

            $empty_inputs = $('.input-group input').filter(function() { return $(this).val() == ""; });

            if( $empty_inputs.length === 0 )
                $('.btn.btn-primary:visible').first().trigger('click');

        }
    });
}

$( document ).ready(function() {

    enter_key_clicks_first_visible_button_if_inputs_not_empty();
});

function fetchByUserId() {
    fetch("/users/" + $('#user_id').val())
}

function authUser(){
    data = {}
    auth_users = {}
    auth_users["email_address"] = $('#auth_email_address').val()
    auth_users["password"] = $('#auth_password').val()
    data["auth_users"] = auth_users
    submit("/users/auth", data, "POST")
}

function createUser(){
    data = {}
    users = {}
    users["email_address"] = $('#email_address').val()
    users["name"] = $('#name').val()
    users["password"] = $('#password').val()
    data["users"] = users
    submit("/users", data, "POST")
}

function fetchService() {
    fetch("/services/" + $('#service_id').val())
}

function fetchArchivedService() {
    fetch("/archived-services?service-id=" + $('#service_id').val())
}

function fetchSupplier() {
    var request = $.ajax({
           url: "/suppliers/" + $('#service_id').val(),
           type: "GET",
           contentType: "application/json",
           headers: commonHeaders()
           });
    request.fail(function (jqXHR, textStatus, errorThrown){
             var obj = JSON.parse(jqXHR.responseText);
             $("#response").html(printHTMLResponse(jqXHR, obj));
         });
    request.done(function (response, textStatus, jqXHR){
              var obj = JSON.parse(jqXHR.responseText);
              $("#response").html(printHTMLResponse(jqXHR, obj));
         });
}

function updateService() {
    var update_details = {}
    var services = {}
    update_details['updated_by'] = 'joeblogs'
    update_details['update_reason'] = 'whateves'
    var value = $('#value').val()
    if(!isNaN(value)) {
        value = parseInt(value,10)
    } else if(value == "true") {
        value = true
    } else if(value == "false") {
        value = false
    }
    services[$('#key').val()] = value

    var update = {}
    update['update_details'] = update_details
    update['services'] = services
    submit("/services/" + $('#service_id').val(), update, "POST")
}

function importService() {
    var update_details = {}
    var services = {}
    update_details['updated_by'] = 'joeblogs'
    update_details['update_reason'] = 'whateves'
    var service = {}
    service['services'] = JSON.parse($('#import-json').val())
    service['update_details'] = update_details
    submit("/services/" + $('#service_id').val(), service, "PUT")
}


function fetch(url) {
    var request = $.ajax({
           url: url,
           type: "GET",
           contentType: "application/json",
           headers: commonHeaders()
           });
    request.fail(function (jqXHR, textStatus, errorThrown){
             var obj = JSON.parse(jqXHR.responseText);
             $("#response").html(printHTMLResponse(jqXHR, obj));
         });
    request.done(function (response, textStatus, jqXHR){
              var obj = JSON.parse(jqXHR.responseText);
              $("#response").html(printHTMLResponse(jqXHR, obj));
         });
}

function submit(url, data, method) {
  var request = $.ajax({
           url: url,
           type: method,
           data : JSON.stringify(data),
           headers: commonHeaders("application/json")
           });
    request.fail(function (jqXHR, textStatus, errorThrown){
             var obj = JSON.parse(jqXHR.responseText);
             $("#response").html(printHTMLResponse(jqXHR, obj));
         });
    request.done(function (response, textStatus, jqXHR){
             var obj = JSON.parse(jqXHR.responseText);
             $("#response").html(printHTMLResponse(jqXHR, obj));
         });
}

function commonHeaders(contentType) {
    var headers = {}

    headers['Authorization'] = 'Bearer ' + $('#bearer-token').val();
    headers['Access-Control-Allow-Origin'] = "*";

    if (contentType != null) {
        headers['Content-type'] = contentType
    }

    return headers;
}

function printHTMLResponse(jqXHR, obj) {
    return "<i><h5>Response Status:</h5> " +  jqXHR.status +
           "<p/><h5>Response Headers:</h5><pre>" + jqXHR.getAllResponseHeaders() +
           "</pre><h5>Response Body:</h5><pre>" + JSON.stringify(obj, null, 4) + "</pre></i>"

}