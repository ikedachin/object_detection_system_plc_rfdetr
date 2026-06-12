'use strict';

//////////////////////////////////////////////
// Websocket for Clock
//////////////////////////////////////////////
const clock_url = 'ws://' + window.location.host + '/get_imgs/ws/time/';
const ws_clock = new WebSocket(clock_url);

console.log("WebSocket for clock:", clock_url);

ws_clock.onmessage = function(event) {
  const data = JSON.parse(event.data);
  // console.log(data);
  let miniClock = document.getElementById('miniClock');
  document.getElementById('miniClock').textContent = data.now_time;
};




//////////////////////////////////////////////
// // Websocket for Camera
//////////////////////////////////////////////
const url   = `ws://${window.location.host}/get_imgs/ws/camera/`;
const ws_movie    = new WebSocket(url);
ws_movie.binaryType = "blob";      // 重要: サーバーからの bytes を Blob として受信

//canvases
const canvas_movie = document.getElementById("movie");
const ctx_movie = canvas_movie.getContext("2d");
const img_movie = new Image();

const canvas_still = document.getElementById("still");
const ctx_still = canvas_still.getContext("2d");
const img_still = new Image(canvas_movie.width, canvas_movie.height);

ws_movie.onmessage = evt => {
  const blob_movie = evt.data;
  const reader_movie = new FileReader();
  // console.log(blob_movie);
  // console.log(evt);
  
  reader_movie.onload = function(event) {
    
    img_movie.onload = () => {
      canvas_movie.width  = img_movie.width;
      canvas_movie.height = img_movie.height;
      ctx_movie.drawImage(img_movie, 0, 0);
    };
    img_movie.src = reader_movie.result;
  };
  reader_movie.readAsDataURL(blob_movie);
};

ws_movie.onclose = () => console.log("WebSocket closed");


//////////////////////////////////////////////
// snapshot
//////////////////////////////////////////////
const snapButton = document.getElementById("snapButton");

snapButton.addEventListener("click", () => {
  const snap_url = `ws://${window.location.host}/get_imgs/ws/snap/`;
  const ws_snap = new WebSocket(snap_url);
  const img_still = new Image();
  
  ws_snap.binaryType = "blob"; 
  
  // console.log("Snapshot button clicked", snap_url);
  
  let send_data = {
    "snap": "True",
    "datetime": new Date().toLocaleString()
  }
  // console.log("Sending snapshot request:", send_data);

  ws_snap.onmessage = evt => {
    console.log("Snapshot received:", evt.data);
    const blob_still = evt.data;
    const reader_still = new FileReader();

    reader_still.onload = function(event) {
      // console.log("Snapshot received:", event.target.result);
      img_still.onload = () => {
        canvas_still.width  = img_still.width;
        canvas_still.height = img_still.height;
        console.log("Still image dimensions:", canvas_still.width, canvas_still.height);
        ctx_still.drawImage(img_still, 0, 0);
      };
      img_still.src = reader_still.result;
    };
    reader_still.readAsDataURL(blob_still);

  };
});
