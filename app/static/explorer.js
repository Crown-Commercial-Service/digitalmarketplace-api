function do_i_work() {
    console.log("yes i do");
}

function fetchService() {
    var request = $.ajax({
           url: "/services/" + $('#service_id').val(),
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

function fetchArchivedService() {
    var request = $.ajax({
           url: "/archived-services?service-id=" + $('#service_id').val(),
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
    services[$('#key').val()] = $('#value').val()

    var update = {}
    update['update_details'] = update_details
    update['services'] = services

    var request = $.ajax({
           url: "/services/" + $('#service_id').val(),
           type: "POST",
           contentType: "application/json",
            data : JSON.stringify(update),
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

function importService() {
    var update_details = {}
    var services = {}
    update_details['updated_by'] = 'joeblogs'
    update_details['update_reason'] = 'whateves'
    var service = {}
    service['services'] = JSON.parse($('#import-json').val())
    service['update_details'] = update_details
    var request = $.ajax({
           url: "/services/" + $('#service_id').val(),
           type: "PUT",
           data : JSON.stringify(service),
           headers: commonHeaders("application/json")
           });
    request.fail(function (jqXHR, textStatus, errorThrown){
             var obj = JSON.parse(jqXHR.responseText);
             $("#response").html(printHTMLResponse(jqXHR, obj));
         });
    request.done(function (response, textStatus, jqXHR){
              $("#response").html("done");
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