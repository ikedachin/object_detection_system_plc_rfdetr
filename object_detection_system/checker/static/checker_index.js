// 判定表示の制御関数
function showWaiting() {
  document.getElementById('waitingResult').style.display = 'block';
  document.getElementById('detectedResult').style.display = 'none';
}
function showResult(text) {
  document.getElementById('waitingResult').style.display = 'none';
  const dr = document.getElementById('detectedResult');
  dr.innerHTML = text; // ←ここをtextContentからinnerHTMLに変更
  dr.style.display = 'block';
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showErrorResult(message) {
  const mainBg = document.getElementById("mainBg");
  const resultCard = document.getElementById("resultCard");
  mainBg.style.background = "#b22222";
  mainBg.style.transition = "background 0.3s";
  resultCard.style.background = "#b22222";
  resultCard.style.color = "#fff";
  resultCard.classList.add('detected');
  showResult(
    '<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:180px;">' +
    '<div style="font-size:1.8rem; font-weight:bold; text-align:center; margin-bottom:0.5em;">エラー</div>' +
    `<div style="font-size:1rem; line-height:1.5; text-align:left;">${escapeHtml(message)}</div>` +
    '</div>'
  );
}

function renderDetectionResult(message) {
  const mainBg = document.getElementById("mainBg");
  const resultCard = document.getElementById("resultCard");
  resultCard.classList.remove('detected');

  if (message.result === false) {
    mainBg.style.background = "#b22222";
    mainBg.style.transition = "background 0.3s";
    resultCard.style.background = "#b22222";
    resultCard.style.color = "#fff";
    resultCard.classList.add('detected');

    let displayValue =
      '<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:180px;">' +
      '<div style="font-size:2.2rem; font-weight:bold; text-align:center; margin-bottom:0.5em;">異常です！</div>';
    for (const [key, val] of Object.entries(message.result_dict || {})) {
      displayValue += `<div>${escapeHtml(key)}: ${escapeHtml(val)}</div>`;
    }
    displayValue += '</div>';
    showResult(displayValue);
  } else if (message.result === true) {
    mainBg.style.background = "#228b22";
    mainBg.style.transition = "background 0.3s";
    resultCard.style.background = "#228b22";
    resultCard.style.color = "#fff";
    resultCard.classList.add('detected');

    let displayValue = "";
    for (const [key, val] of Object.entries(message.result_dict || {})) {
      displayValue += `${escapeHtml(key)}: ${escapeHtml(val)}<br>`;
    }
    showResult(displayValue || "OK");
  } else {
    showErrorResult(message.error || "判定結果を取得できませんでした");
  }
}
'use strict';

const mainDisplay = document.getElementById("mainDisplays");
let numValue = "";

//////////////////////////////////////////////
// Websocket for Clock
//////////////////////////////////////////////
const clock_url = `ws://${window.location.host}/checker/ws/time/`;
const ws_clock = new WebSocket(clock_url);
window.ws_clock = ws_clock;

console.log("WebSocket for clock:", clock_url);

ws_clock.onmessage = function(event) {
  const data = JSON.parse(event.data);
  if (data.type === 'plc_status') {
    if (data.status === 'error') {
      showErrorResult(data.error || 'PLCトリガーによる判定に失敗しました');
    } else if (data.status === 'completed') {
      renderDetectedImageFromDataUrl(data.image_data_url);
      renderDetectionResult(data);
    }
    return;
  }
  // console.log(data);
  let miniClock = document.getElementById('miniClock');
  document.getElementById('miniClock').textContent = data.now_time;
};

// ページ離脱時にWSを閉じてサーバ側disconnectを確実に発火させる
function cleanupCheckerSockets() {
  try {
    if (window.ws_clock && (window.ws_clock.readyState === WebSocket.OPEN || window.ws_clock.readyState === WebSocket.CONNECTING)) {
      window.ws_clock.close(1000, 'page leaving');
    }
  } catch (e) {}
  window.ws_clock = null;
}

window.addEventListener('pagehide', cleanupCheckerSockets);
window.addEventListener('beforeunload', cleanupCheckerSockets);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) cleanupCheckerSockets();
});

//////////////////////////////////////////////
// Canvas aspect ratio management
//////////////////////////////////////////////
function maintainCanvasAspectRatio(canvas, img) {
  // 画像の元の縦横比を取得
  const imgAspectRatio = img.naturalWidth / img.naturalHeight;
  
  // canvasの現在のサイズを取得
  const canvasRect = canvas.getBoundingClientRect();
  const canvasAspectRatio = canvasRect.width / canvasRect.height;
  
  // アスペクト比に基づいてcanvasのサイズを調整
  if (imgAspectRatio > canvasAspectRatio) {
    // 画像が横長の場合、幅を基準にする
    canvas.style.width = '100%';
    canvas.style.height = 'auto';
  } else {
    // 画像が縦長の場合、高さを基準にする
    canvas.style.height = '100%';
    canvas.style.width = 'auto';
  }
  
  // canvasの実際のピクセルサイズを画像サイズに合わせる
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
}

function drawImageWithAspectRatio(canvas, ctx, img) {
  // アスペクト比を維持してcanvasサイズを設定
  maintainCanvasAspectRatio(canvas, img);
  
  // 画像をcanvasに描画（アスペクト比を保持）
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  // 判定結果カードの高さをcanvasの表示サイズに合わせる
  const resultCard = document.getElementById("resultCard");
  const canvasRect = canvas.getBoundingClientRect();
  resultCard.style.height = canvasRect.height + "px";
  // 画像カードの色を元に戻す
  const imageCard = document.getElementById("imageCard");
  imageCard.style.background = "#23272b";
  imageCard.style.color = "#f4f6f8";
  // 初期状態で画像カードの色を薄いグレーに
  window.addEventListener('DOMContentLoaded', function() {
    const imageCard = document.getElementById("imageCard");
    if (imageCard) {
      imageCard.style.background = "#bfc7cc";
      imageCard.style.color = "#23272b";
    }
  });
}

//////////////////////////////////////////////
// click on 確認 button
//////////////////////////////////////////////
const snapButton = document.getElementById("snapButton");
const resetPlcResultButton = document.getElementById("resetPlcResultButton");
const detectedImage = document.getElementById("detectedImage");
const detectedResult = document.getElementById("detectedResult");
const ctx_detected = detectedImage.getContext("2d");
let detectionInProgress = false;

function renderDetectedImageFromDataUrl(dataUrl) {
  if (!dataUrl) {
    return;
  }

  const detected_img = new Image();
  detected_img.onload = () => {
    console.log("Image loaded and rendered");
    drawImageWithAspectRatio(detectedImage, ctx_detected, detected_img);
    console.log("Detected image dimensions:", detected_img.naturalWidth, detected_img.naturalHeight);
  };
  detected_img.onerror = () => {
    showErrorResult("判定画像の表示に失敗しました");
  };
  detected_img.src = dataUrl;
}

function setDetectionInProgress(inProgress) {
  detectionInProgress = inProgress;
  if (snapButton) {
    snapButton.disabled = inProgress;
  }
}

function resetCheckerDisplay() {
  const mainBg = document.getElementById("mainBg");
  const resultCard = document.getElementById("resultCard");
  const imageCard = document.getElementById("imageCard");

  ctx_detected.clearRect(0, 0, detectedImage.width, detectedImage.height);
  detectedImage.removeAttribute("width");
  detectedImage.removeAttribute("height");
  detectedImage.style.width = "100%";
  detectedImage.style.height = "auto";

  mainBg.style.background = "transparent";
  resultCard.style.background = "#fff";
  resultCard.style.color = "#23272b";
  resultCard.style.height = "";
  resultCard.classList.remove('detected');
  imageCard.style.background = "#e3f2fd";
  imageCard.style.color = "#23272b";
  detectedResult.innerHTML = "";
  showWaiting();
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function resetPlcResultSignals() {
  if (!confirm("PLC結果ビットをリセットします。設備側が結果を読み取り済みであることを確認してください。")) {
    return;
  }

  resetPlcResultButton.disabled = true;
  fetch('/checker/api/reset_plc_result/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ reset: true }),
  })
  .then(response => response.json())
  .then(data => {
    if (!data.success) {
      throw new Error(data.error || 'PLC結果ビットのリセットに失敗しました');
    }
    console.log("PLC result reset:", data.reset_targets);
    resetCheckerDisplay();
    alert(data.message);
  })
  .catch(error => {
    console.error("PLC result reset error:", error);
    alert("PLC結果ビットのリセットに失敗しました: " + error.message);
  })
  .finally(() => {
    resetPlcResultButton.disabled = false;
  });
}

if (resetPlcResultButton) {
  resetPlcResultButton.addEventListener("click", resetPlcResultSignals);
}

snapButton.addEventListener("click", () => {
  if (detectionInProgress) {
    console.log("Detection is already in progress.");
    return;
  }
  console.log("=== CONFIRM BUTTON CLICKED ===");
  console.log("Button element:", snapButton);
  console.log("Timestamp:", new Date().toISOString());
  
  // まずモデルの状態をチェック
  console.log("=== Checking model status ===");
  fetch('/checker/api/check_model_status/')
  .then(response => {
    console.log("=== Model status response ===");
    console.log("Response status:", response.status);
    console.log("Response OK:", response.ok);
    return response.json();
  })
  .then(data => {
    console.log("=== Model status data ===");
    console.log("Status data:", data);
    console.log("Model status:", data.status);
    
    if (data.status === 'loaded') {
      console.log("=== Model is loaded, starting detection ===");
      detect();
    } else if (data.status === 'loading') {
      console.log("=== Model is loading ===");
      showErrorResult("モデルロード中です。しばらくお待ちください。");
    } else {
      console.log("=== Model not loaded ===");
      showErrorResult("モデルがロードされていません。プロジェクトと学習モデルを選択してください。");
    }
  })
  .catch(error => {
    console.error('=== Model status check error ===');
    console.error('Error object:', error);
    console.error('Error message:', error.message);
    console.error('Error stack:', error.stack);
    // エラーが発生してもdetect()を実行してみる
    console.log("=== Proceeding with detect() despite error ===");
    detect();
  });
});

//////////////////////////////////////////////
// push numpad 0
//////////////////////////////////////////////
// キーボードのリターン、「０」を押したとき
let lastKeyDownTime = 0; // キーダウン1回目の初期値

window.addEventListener('keydown', function(event) {
  // エンターキーが押されたかどうかを確認します
  const currentTime = new Date().getTime();
  if (event.code === "Enter") {
      if (!detectionInProgress && currentTime - lastKeyDownTime > 500) {
          console.log(event.code);
          detect();
      } else {
          console.log('key was pressed multiple times in a short period of time');
      }
  } else if (event.code === "Numpad0") {
      if (!detectionInProgress && currentTime - lastKeyDownTime > 500){
          console.log(event.code);
          detect();
      } else {
          console.log('key was pressed multiple times in a short period of time');
      }
  }
  lastKeyDownTime = currentTime;
})

//////////////////////////////////////////////
function detect() {
  if (detectionInProgress) {
    console.log("Detection is already in progress.");
    return;
  }
  console.log("=== DETECT FUNCTION CALLED ===");
  console.log("Timestamp:", new Date().toISOString());
  setDetectionInProgress(true);
  
  // 判定待ち状態に設定
  showWaiting();
  
  const confirm_url = `ws://${window.location.host}/checker/ws/confirm/`;
  console.log("=== WebSocket URL ===", confirm_url);
  console.log("Window location host:", window.location.host);
  console.log("Window location:", window.location);
  
  const ws_snap = new WebSocket(confirm_url);
  
  ws_snap.binaryType = "blob"; 
  
  console.log("=== WebSocket object created ===");
  console.log("WebSocket readyState:", ws_snap.readyState);
  console.log("WebSocket URL:", ws_snap.url);
  
  let send_data = {
    "snap": "True",
    "datetime": new Date().toLocaleString(),
  }
  
  console.log("=== Send data prepared ===", send_data);

  // 接続タイムアウトを設定
  let connectionTimeout = setTimeout(() => {
    console.error("=== WebSocket connection timeout ===");
    ws_snap.close();
    showErrorResult("接続がタイムアウトしました。再度お試しください。");
    setDetectionInProgress(false);
  }, 10000); // 10秒でタイムアウト

  // WebSocket接続成功時にメッセージを送信
  ws_snap.onopen = function(event) {
    console.log("=== WebSocket connection opened ===");
    console.log("Event:", event);
    console.log("WebSocket readyState:", ws_snap.readyState);
    clearTimeout(connectionTimeout); // タイムアウトをクリア
    
    // 少し待ってからメッセージを送信
    setTimeout(() => {
      console.log("=== Sending snapshot request ===");
      console.log("Data to send:", send_data);
      console.log("JSON string:", JSON.stringify(send_data));
      ws_snap.send(JSON.stringify(send_data));
      console.log("=== Message sent ===");
    }, 100);
  };

  // エラーハンドリング
  ws_snap.onerror = function(error) {
    console.error("=== WebSocket error ===");
    console.error("Error event:", error);
    console.error("WebSocket readyState:", ws_snap.readyState);
    console.error("WebSocket URL:", ws_snap.url);
    clearTimeout(connectionTimeout);
    showErrorResult("WebSocket接続エラーが発生しました。モデルがロードされているか確認してください。");
    setDetectionInProgress(false);
  };

  // 接続終了時の処理
  ws_snap.onclose = function(event) {
    console.log("=== WebSocket connection closed ===");
    console.log("Close event:", event);
    console.log("Close code:", event.code);
    console.log("Close reason:", event.reason);
    console.log("Was clean:", event.wasClean);
    clearTimeout(connectionTimeout);
    setDetectionInProgress(false);
    
    if (event.code !== 1000 && event.code !== 1001) {
      console.error("=== WebSocket closed unexpectedly ===");
      console.error("Close code:", event.code);
      console.error("Close reason:", event.reason);
      if (event.code === 1006) {
        showErrorResult("サーバーとの接続が予期せず切断されました。モデルがロードされているか確認してください。");
      }
    }
  };

  ws_snap.onmessage = evt => {
    console.log("=== WebSocket message received ===");
    
    if (evt.data instanceof Blob) {
      console.log("Received image data (Blob):", evt.data.size, "bytes");
      const blob_still = evt.data;
      const detected = new FileReader();
  
      detected.onload = function(event) {
        renderDetectedImageFromDataUrl(detected.result);
      };
      detected.readAsDataURL(blob_still);
    } else {
      console.log("Received text data:", evt.data);
      
      try {
        let message = JSON.parse(evt.data);
        console.log("Parsed message:", message);
        
        // エラーメッセージの処理
        if (message.error) {
          console.error("=== Server error ===", message.error);
          showErrorResult(message.error);
          setDetectionInProgress(false);
          return;
        }
        
        console.log("Detection result:", message.result);
        console.log("result_dict:", message.result_dict);
        
        renderDetectionResult(message);
      } catch (parseError) {
        console.error("Error parsing JSON message:", parseError);
        console.error("Raw message data:", evt.data);
        showErrorResult("サーバーからの応答の解析に失敗しました");
        setDetectionInProgress(false);
      }
    }
  }
}
