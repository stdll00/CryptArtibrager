'use strict'
//require babel-node
//npm install -g babel-cli
//npm install -g sockjs pm2
// pm2 start bitpoint.js --interpreter babel-node
//

// websocketで価格を取り、保存し続ける。

const request = require('request');
const SockJS = require('sockjs-client');
const fs = require('fs');
const os = require('os');

const USERNAME = "hoge@mail.com";
const PASSWORD = "SHA256_HASHED_PASSEORD";

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const hash = PASSWORD;
var jsonpath = '/var/www/html/bitpoint/'
if((os.platform()=='darwin')){
    jsonpath= ""
}

request.get(`https://public.bitpoint.co.jp/bpj-api/login?username=${USERNAME}&password=${hash}`,
            (error, response, body) => {
              const access_token = JSON.parse(body)['access_token'];

              const sock = new SockJS(`https://public.bitpoint.co.jp/bpj-api/twoWay?access_token=${access_token}`);

              sock.onopen = function() {
                setInterval(function () {
                    sock.send('{"currencyCd1":"BTC","currencyCd2":"JPY"}');
                },30)
              };

              sock.onmessage = function(e) {
                if(e.data[0]=="[") {
                    let jsondata= JSON.parse(e.data);
                    let currency =  jsondata[0]['currencyCd1'];
                    fs.writeFileSync(jsonpath+currency+".json", e.data);// ,error => {console.error("error when write")});
                }
                //console.log(e.data);

              };

              sock.onclose = function() {
                //console.log('close');
                process.exit(1);
              };
});
