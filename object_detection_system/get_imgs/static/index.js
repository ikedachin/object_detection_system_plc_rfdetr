'use strict';


// Websocket for Clock
const ws_clock = new WebSocket('ws://' + window.location.host + '/get_imgs/ws/time/');

ws_clock.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // console.log(data);
    let miniClock = document.getElementById('miniClock');
    document.getElementById('miniClock').textContent = data.now_time;
};
