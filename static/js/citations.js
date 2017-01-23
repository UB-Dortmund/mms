/**
 * Created by hagenbruch on 08.05.14.
 */

/**
 * USAGE:
 *   <script src="https://static.ub.rub.de/bibliographie/js/citations.js" type="text/javascript"></script>
 *   <script type="text/javascript">window.onload = function(){listCitations({ "gnd": "1068269154", "style": "american-geophysical-union", "group_by_year": true, locale: "en-US", agent: "chair" })}</script>
 *
 * SEE ALSO: http://bibliographie-trac.ub.rub.de/wiki/Publikationslisten
 */

var XMLHttpFactories = [
    function () {return new XMLHttpRequest()},
    function () {return new ActiveXObject("Msxml2.XMLHTTP")},
    function () {return new ActiveXObject("Msxml3.XMLHTTP")},
    function () {return new ActiveXObject("Microsoft.XMLHTTP")}
];

function createXMLHTTPObject() {
    var xmlhttp = false;
    for (var i=0;i<XMLHttpFactories.length;i++) {
        try {
            xmlhttp = XMLHttpFactories[i]();
        }
        catch (e) {
            continue;
        }
        break;
    }
    return xmlhttp;
}
function listCitations(params){
    var req = createXMLHTTPObject();
    var target_id = params.target_id || 'citationlist';
    // https://bibliographie.ub.rub.de/chair/1068269154/bibliography/american-geophysical-union?format=js
    req.open('GET', 'https://bibliographie.ub.rub.de/' + params.agent + '/' + params.gnd + '/bibliography/' + params.style + '?format=html&' + Object.keys(params).map(function(key){return key + '=' + params[key];}).join('&'));

    req.onreadystatechange = function(){
        if(req.readyState === 4 && (req.status === 200 || req.status === 304)){
            var cl = document.getElementById(target_id);
            cl.innerHTML = req.responseText;
        }
    }
    req.send(null);
}