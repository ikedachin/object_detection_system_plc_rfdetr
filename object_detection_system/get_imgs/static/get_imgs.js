'use strict';

// グローバル設定と関数
//////////////////////////////////////////////
// 設定反映後のみcanvas描画・サイズ変更を許可する制御
window.isCameraSettingApplied = false; // 設定反映済みフラグ
window.frameCount = 0; // 受信フレーム数
window.lastFrameTime = null; // 最終受信時刻

// カメラ接続状況
window.updateDebugInfo = function() {
    // 設定反映状態
    const settingElement = document.getElementById('debugCameraSettingApplied');
    if (settingElement) {
        if (window.isCameraSettingApplied) {
            settingElement.textContent = '適用済み';
            settingElement.className = 'badge bg-success';
        } else {
            settingElement.textContent = '未設定';
            settingElement.className = 'badge bg-secondary';
        }
    }
    
    // WebSocket状態
    const wsElement = document.getElementById('debugWebSocketState');
    if (wsElement) {
        if (window.ws_movie && window.ws_movie.readyState === WebSocket.OPEN) {
            wsElement.textContent = '接続中';
            wsElement.className = 'badge bg-success';
        } else if (window.ws_movie && window.ws_movie.readyState === WebSocket.CONNECTING) {
            wsElement.textContent = '接続中...';
            wsElement.className = 'badge bg-warning';
        } else {
            wsElement.textContent = '未接続';
            wsElement.className = 'badge bg-secondary';
        }
    }
    
    // フレーム数
    const frameElement = document.getElementById('debugFrameCount');
    if (frameElement) {
        frameElement.textContent = window.frameCount;
        if (window.frameCount > 0) {
            frameElement.className = 'badge bg-success';
        }
    }

    // 最終受信時刻
    const timeElement = document.getElementById('debugLastFrameTime');
    if (timeElement) {
        if (window.lastFrameTime) {
            timeElement.textContent = window.lastFrameTime.toLocaleTimeString();
            timeElement.className = 'badge bg-success';
        } else {
            timeElement.textContent = '-';
            timeElement.className = 'badge bg-secondary';
        }
    }
};

// 定期的にデバッグ情報を更新
setInterval(window.updateDebugInfo, 1000);

window.getSelectedImageSize = function() {
    // セレクトボックスから選択値を取得し、width/heightを返す
    const size = document.getElementById('imageSize')?.value;
    switch(size) {
        case 'HD1080p': return {w:1920, h:1080};
        case 'HD720p':  return {w:1280, h:720};
        case 'SD480p':  return {w:640,  h:480};
        case 'SD360p':  return {w:480,  h:360};
        default:        return {w:640,  h:480};
    }
};

// 設定反映後のみ描画許可
function isCameraSettingApplied() {
    return window.isCameraSettingApplied === true;
}

//////////////////////////////////////////////
// Websocket for Clock
//////////////////////////////////////////////
const clock_url = 'ws://' + window.location.host + '/get_imgs/ws/time/';
window.ws_clock = new WebSocket(clock_url);

console.log("WebSocket for clock:", clock_url);

window.ws_clock.onmessage = function(event) {
  const data = JSON.parse(event.data);
  // console.log(data);
  let miniClock = document.getElementById('miniClock');
  document.getElementById('miniClock').textContent = data.now_time;
};

//////////////////////////////////////////////
// 離脱時クリーンアップ（bfcache対策含む）
//////////////////////////////////////////////

window.cleanupGetImgsSockets = function() {
    // camera
    if (window.ws_movie) {
        try {
            if (window.ws_movie.readyState === WebSocket.OPEN || window.ws_movie.readyState === WebSocket.CONNECTING) {
                window.ws_movie.close(1000, 'page leaving');
            }
        } catch (e) {}
        window.ws_movie = null;
    }

    // clock
    if (window.ws_clock) {
        try {
            if (window.ws_clock.readyState === WebSocket.OPEN || window.ws_clock.readyState === WebSocket.CONNECTING) {
                window.ws_clock.close(1000, 'page leaving');
            }
        } catch (e) {}
        window.ws_clock = null;
    }

    // revoke object URL
    if (window.currentObjectURL) {
        try { URL.revokeObjectURL(window.currentObjectURL); } catch (e) {}
        window.currentObjectURL = null;
    }
};

// ナビゲーション/戻る進む(bfcache)/タブ非表示で確実に停止
window.addEventListener('pagehide', () => window.cleanupGetImgsSockets());
window.addEventListener('beforeunload', () => window.cleanupGetImgsSockets());
document.addEventListener('visibilitychange', () => {
    if (document.hidden) window.cleanupGetImgsSockets();
});

//////////////////////////////////////////////
// // Websocket for Camera
//////////////////////////////////////////////

// DOM読み込み完了後に初期化
let canvas_movie, ctx_movie, img_movie;
let canvas_still, ctx_still, img_still;

// DOM読み込み完了を待つ
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM読み込み完了、キャンバス初期化開始');
    
    canvas_movie = document.getElementById("movie");
    ctx_movie = canvas_movie?.getContext("2d");
    img_movie = new Image();

    canvas_still = document.getElementById("still");
    ctx_still = canvas_still?.getContext("2d");
    img_still = new Image();
    
    console.log('Canvas elements check:', {
        canvas_movie: !!canvas_movie,
        ctx_movie: !!ctx_movie,
        canvas_still: !!canvas_still,
        ctx_still: !!ctx_still
    });
    
    if (!canvas_movie || !canvas_still) {
        console.error('Canvas elements not found - HTML構造を確認してください');
        return;
    }
    
    console.log('キャンバス初期化完了');
});

// --- 追加: カメラWebSocketの動的接続・切断制御 ---
window.ws_movie = null;
window.currentObjectURL = null;
window.initCameraWebSocket = function() {
    // 既存接続があれば切断
    if (window.ws_movie) {
        try { window.ws_movie.close(); } catch(e) {}
        window.ws_movie = null;
    }
    const url = `ws://${window.location.host}/get_imgs/ws/camera/`;
    const ws = new WebSocket(url);
    ws.binaryType = "blob";
    window.ws_movie = ws;
    
    ws.onopen = function() {
        console.log('Camera WebSocket connected to:', url);
        // window.updateDebugInfo(); // デバッグ情報更新
        // 設定反映時に全ての設定を送信
        const imageSize = document.getElementById('imageSize')?.value || 'SD480p';
        const fps = document.getElementById('fps')?.value || '30';
        const interval = document.getElementById('interval')?.value || '60';
        const projectName = window.getCurrentProjectName() || '';
        
        const settings = {
            image_size: imageSize,
            fps: fps,
            interval: interval,
            project_name: projectName
        };
        
        ws.send(JSON.stringify(settings));
        console.log('カメラ設定送信:', settings);
        console.log('WebSocket readyState:', ws.readyState);
    };
    
    ws.onmessage = evt => {
        console.log('📥 WebSocketメッセージ受信:', {
            dataType: typeof evt.data,
            isCameraSettingApplied: window.isCameraSettingApplied,
            dataSize: evt.data instanceof Blob ? evt.data.size : evt.data.length
        });
        
        if (!window.isCameraSettingApplied) {
            console.log('⏸️ カメラ設定が適用されていないため、フレームを無視します');
            return;
        }
        
        if (typeof evt.data === 'string') {
            try {
                const data = JSON.parse(evt.data);
                console.log('📨 JSON メッセージ:', data);
                
                // カメラ開始メッセージの場合はFPS情報も表示
                if (data.message && data.fps) {
                    console.log(`🎥 カメラ設定確認: FPS=${data.fps}, 保存間隔=${data.save_interval}秒`);
                }
                
                // エラーメッセージの場合は表示
                if (data.error) {
                    console.error('❌ カメラエラー:', data.error);
                    alert('カメラエラー: ' + data.error);
                }
            } catch(e) {
                console.log('📄 非JSON文字列メッセージ:', evt.data);
            }
            return;
        }
        
        // Blobデータの場合（画像）
        console.log('🖼️ 画像フレーム受信:', evt.data.size, 'bytes', 'type:', evt.data.type);
        
        // デバッグ情報を更新
        window.frameCount++;
        window.lastFrameTime = new Date();
        // window.updateDebugInfo();
        const blob_movie = evt.data;
        if (window.currentObjectURL) {
            URL.revokeObjectURL(window.currentObjectURL);
            window.currentObjectURL = null;
        }
        window.currentObjectURL = URL.createObjectURL(blob_movie);
        
        // canvas要素が存在するかチェック
        if (!canvas_movie || !ctx_movie || !img_movie) {
            console.error('Canvas elements not initialized');
            return;
        }
        
        console.log('Canvas状態:', {
            canvas_movie: !!canvas_movie,
            ctx_movie: !!ctx_movie,
            img_movie: !!img_movie,
            canvas_width: canvas_movie.width,
            canvas_height: canvas_movie.height
        });
        
        img_movie.onload = () => {
            console.log('画像読み込み完了:', img_movie.width, 'x', img_movie.height);
            
            // キャンバスサイズを画像に合わせて設定
            if (img_movie.width > 0 && img_movie.height > 0) {
                canvas_movie.width = img_movie.width;
                canvas_movie.height = img_movie.height;
                console.log('キャンバスサイズ更新:', canvas_movie.width, 'x', canvas_movie.height);
                
                // windowに設定されているsetMovieCanvasSizeがあれば使用
                if (window.setMovieCanvasSize) {
                    window.setMovieCanvasSize(img_movie);
                }
            }
            
            ctx_movie.clearRect(0, 0, canvas_movie.width, canvas_movie.height);
            ctx_movie.drawImage(img_movie, 0, 0, canvas_movie.width, canvas_movie.height);
            console.log('フレーム描画完了');
        };
        
        img_movie.onerror = (error) => {
            console.error('画像読み込みエラー:', error);
        };
        
        console.log('画像src設定:', window.currentObjectURL);
        img_movie.src = window.currentObjectURL;
    };
    
    ws.onclose = (event) => {
        console.log("Camera WebSocket closed:", event.code, event.reason);
        window.ws_movie = null;
        // window.updateDebugInfo(); // デバッグ情報更新
    };
    
    ws.onerror = (e) => {
        console.error('Camera WebSocket error', e);
        console.log('WebSocket readyState:', ws.readyState);
        console.log('WebSocket URL:', url);
        // window.updateDebugInfo(); // デバッグ情報更新
    };
};
window.closeCameraWebSocket = function() {
    if (window.ws_movie) {
        try { window.ws_movie.close(); } catch(e) {}
        window.ws_movie = null;
    }
    if (window.currentObjectURL) {
        URL.revokeObjectURL(window.currentObjectURL);
        window.currentObjectURL = null;
    }
};
// ページ離脱時に必ずカメラを止める
window.addEventListener('beforeunload', function() {
    window.closeCameraWebSocket();
});


//////////////////////////////////////////////
// snapshot
//////////////////////////////////////////////
// snapButtonのイベントリスナーもDOMContentLoaded内で設定
document.addEventListener('DOMContentLoaded', function() {
    const snapButton = document.getElementById("snapButton");
    
    if (snapButton) {
        snapButton.addEventListener("click", () => {
          if (!window.isCameraSettingApplied) {
            alert('先にプロジェクト設定を反映してください');
            return;
          }
          const snap_url = `ws://${window.location.host}/get_imgs/ws/snap/`;
          const ws_snap = new WebSocket(snap_url);
          const img_still_snap = new Image();
          ws_snap.binaryType = "blob"; 

          // プロジェクト名を取得
          const projectName = window.getCurrentProjectName() || '';

          let send_data = {
            "snap": "True",
            "datetime": new Date().toLocaleString(),
            "project_name": projectName
          }

          ws_snap.onopen = function() {
            ws_snap.send(JSON.stringify(send_data));
          };

          ws_snap.onmessage = evt => {
            console.log("Snapshot received:", evt.data);
            const blob_still = evt.data;
            const reader_still = new FileReader();

            reader_still.onload = function(event) {
              if (!canvas_still || !ctx_still) {
                console.error('Still canvas elements not initialized');
                return;
              }
              img_still_snap.onload = () => {
                canvas_still.width  = img_still_snap.width;
                canvas_still.height = img_still_snap.height;
                console.log("Still image dimensions:", canvas_still.width, canvas_still.height);
                ctx_still.drawImage(img_still_snap, 0, 0);
              };
              img_still_snap.src = reader_still.result;
            };
            reader_still.readAsDataURL(blob_still);
          };
        });
    }
    
    // 設定反映ボタンでプロジェクト用フォルダ作成APIを呼ぶ
    const applySettingsBtn = document.getElementById('applySettingsBtn');
    if (applySettingsBtn) {
      applySettingsBtn.addEventListener('click', function() {
        // すでに設定反映済みなら何もしない
        if (window.isCameraSettingApplied) return;
        
        const projectName = getCurrentProjectName();
        if (!projectName) {
          alert('プロジェクトを選択してください');
          return;
        }
        
        console.log('設定適用処理は、HTMLテンプレート内で実行されます');
      });
    }

    // 設定再編集ボタン
    const editBtn = document.getElementById('editSettingsBtn');
    if (editBtn) {
      editBtn.addEventListener('click', function() {
        console.log('再設定ボタンの処理は、HTMLテンプレート内で実行されます');
      });
    }
});

//////////////////////////////////////////////
// 設定適用関数
//////////////////////////////////////////////
window.applySettings = function(settings) {
    console.log('設定適用開始:', settings);
    console.log('DOM要素確認:', {
        canvas_movie: !!canvas_movie,
        canvas_still: !!canvas_still,
        ctx_movie: !!ctx_movie,
        ctx_still: !!ctx_still
    });
    
    // 設定反映フラグを立てる
    window.isCameraSettingApplied = true;
    console.log('設定反映フラグを有効にしました');
    
    // カメラの初期化
    if (window.ws_movie) {
        console.log('既存のWebSocket接続を切断中...');
        window.closeCameraWebSocket();
    }
    
    // 少し遅延してからカメラWebSocketを初期化
    console.log('WebSocket再接続を開始します...');
    setTimeout(() => {
        window.initCameraWebSocket();
    }, 500);
    
    // キャンバスサイズを設定
    const size = window.getSelectedImageSize();
    console.log('選択された画像サイズ:', size);
    
    if (canvas_movie) {
        canvas_movie.width = size.w;
        canvas_movie.height = size.h;
        console.log('Movie canvas size set to:', size.w, 'x', size.h);
    }
    if (canvas_still) {
        canvas_still.width = size.w;
        canvas_still.height = size.h;
        console.log('Still canvas size set to:', size.w, 'x', size.h);
    }
    
    console.log('設定適用完了');
};
