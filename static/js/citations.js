/**
 * Created by hagenbruch on 08.05.14.
 * Last modified by hagbeck on 2017-02-12
 */

/**
 * USAGE:
 *   <script type="application/javascript" src="https://www.ub.tu-dortmund.de/js/citations.js"></script>
 *   <script type="text/javascript">window.onload = function(){listCitations({ "gnd": "1068269154", "style": "american-geophysical-union", "group_by_year": true, locale: "en-US", agent: "chair" })}</script>
 *
 * SEE ALSO: https://hochschulbibliographie.ub.tu-dortmund.de/beta/embed_works
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

    var target_id = 'citationlist';

    if (params.target_id != null || params.target_id != '') {
        target_id = params.target_id;
        delete params['target_id'];
    }

    agent = params.agent;
    delete params['agent'];
    gnd = params.gnd;
    delete params['gnd'];
    style = params.style;
    delete params['style'];

    //var baseurl = 'http://localhost:5006';
    var baseurl = 'https://hochschulbibliographie.ub.tu-dortmund.de/beta';
    //var baseurl = 'https://bibliographie.ub.rub.de';
    req.open('GET', baseurl + '/' + agent + '/' + gnd + '/bibliography/' + style + '?format=html&' + Object.keys(params).map(function(key){return key + '=' + params[key];}).join('&'));

    req.onreadystatechange = function(){
        if(req.readyState === 4 && (req.status === 200 || req.status === 304)){
            var cl = document.getElementById(target_id);
            cl.innerHTML = req.responseText;
        }
    }
    req.send(null);
}