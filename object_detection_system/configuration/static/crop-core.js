// crop-core.js - メインのCropper機能とグローバル変数

// グローバル変数
let cropper;
const sourceImage = document.getElementById('source-image');
const previewCanvas = document.getElementById('preview-canvas');
const previewCtx = previewCanvas.getContext('2d');
const cropInfo = document.getElementById('crop-info');
const folderPathSelect = document.getElementById('folder-path');
const customPathInput = document.getElementById('custom-path');
const fileListDiv = document.getElementById('file-list');
let uploadedImageData = null;
let selectedImagePath = null;
let selectedFolderPath = null; // 新しい変数を追加

// 640×640 のターゲット解像度 (正方形)
const TARGET_WIDTH = 640;
const TARGET_HEIGHT = 640;

// 座標蓄積機能
let cropCoordinates = [];
let coordinateCounter = 0;

// 画像ごとの座標を保存する辞書
let imageCoordinatesMap = new Map();

// 画像ナビゲーション機能
let currentImageList = [];
let currentImageIndex = 0;
let currentBasePath = '';

// Cropper初期化関数
function initializeCropper() {
    // 既存のcropperを破棄
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
    
    cropper = new Cropper(sourceImage, {
        aspectRatio: 1,  // 正方形（1:1）の比率
        viewMode: 1,     // 切り抜き範囲がキャンバス内に制限される
        dragMode: 'move',
        autoCropArea: 0.6,  // 初期切り抜きエリアを少し小さく
        restore: false,
        guides: true,
        center: true,
        highlight: false,
        cropBoxMovable: true,
        cropBoxResizable: true,  // サイズ変更可能に変更
        toggleDragModeOnDblclick: false,
        responsive: true,  // レスポンシブ対応
        checkCrossOrigin: false,
        checkOrientation: true,  // EXIF情報による画像向き自動修正を有効化
        
        // マウススクロール（ホイール）によるズームを無効化
        zoomOnWheel: false,
        wheelZoomRatio: 0,
        
        // コンテナの最大サイズを制限
        minContainerWidth: 300,
        minContainerHeight: 300,
        
        // 切り抜きボックスの最小サイズを設定
        minCropBoxWidth: 100,
        minCropBoxHeight: 100,
        
        // リアルタイムプレビュー更新
        crop: function(event) {
            updatePreview(event.detail);
            updateCropInfo(event.detail);
        },
        
        // Cropper初期化完了時の処理
        ready: function() {
            // 初期状態で中央に配置
            this.cropper.setDragMode('move');
            // コンテナサイズ制限を適用
            applyCropperConstraints();
            // ホイールズームを無効化
            disableWheelZoom();
        }
    });
}

// エラーハンドリング付きCropper初期化関数
function initializeCropperSafely() {
    try {
        initializeCropper();
    } catch (error) {
        console.error('Cropper initialization failed:', error);
        // フォールバック: 既存のCropperを確実に破棄
        if (cropper) {
            try {
                cropper.destroy();
            } catch (destroyError) {
                console.warn('Cropper destroy failed:', destroyError);
            }
            cropper = null;
        }
        // 再試行
        setTimeout(() => {
            try {
                initializeCropper();
            } catch (retryError) {
                console.error('Cropper retry initialization failed:', retryError);
                alert('画像の読み込みに失敗しました。ページを再読み込みしてください。');
            }
        }, 500);
    }
}

// Cropper初期化後の制限適用
function applyCropperConstraints() {
    setTimeout(() => {
        enforceContainerLimits();
        
        // 切り抜きエリアがコンテナからはみ出ないように調整
        if (cropper) {
            const cropBoxData = cropper.getCropBoxData();
            const containerData = cropper.getContainerData();
            
            // 切り抜きボックスがコンテナより大きい場合は調整
            if (cropBoxData.width > containerData.width || cropBoxData.height > containerData.height) {
                const size = Math.min(containerData.width, containerData.height) * 0.6;
                cropper.setCropBoxData({
                    left: (containerData.width - size) / 2,
                    top: (containerData.height - size) / 2,
                    width: size,
                    height: size
                });
            }
        }
    }, 100);
}

// ウィンドウリサイズ時のCropper制限維持
function enforceContainerLimits() {
    if (cropper) {
        const container = document.querySelector('.cropper-container');
        if (container) {
            // コンテナサイズを強制的に制限
            const maxWidth = Math.min(800, window.innerWidth - 40);
            const maxHeight = Math.min(600, window.innerHeight - 200);
            
            container.style.maxWidth = maxWidth + 'px';
            container.style.maxHeight = maxHeight + 'px';
            
            // Cropperの再計算
            cropper.resize();
        }
    }
}

// リアルタイムプレビュー更新
function updatePreview(cropData) {
    if (!cropper) return;

    const canvas = cropper.getCroppedCanvas({
        width: TARGET_WIDTH,
        height: TARGET_HEIGHT,
        imageSmoothingEnabled: true,
        imageSmoothingQuality: 'high',
        fillColor: '#fff'  // 背景色を白に設定
    });

    if (canvas) {
        previewCtx.clearRect(0, 0, TARGET_WIDTH, TARGET_HEIGHT);
        previewCtx.drawImage(canvas, 0, 0, TARGET_WIDTH, TARGET_HEIGHT);
    }
}

// サイズ調整機能 - 正方形を維持しながらサイズを変更
function adjustCropSize(delta) {
    if (!cropper) return;
    
    const currentCropBoxData = cropper.getCropBoxData();
    const containerData = cropper.getContainerData();
    
    // 現在のサイズを取得
    const currentSize = Math.min(currentCropBoxData.width, currentCropBoxData.height);
    const newSize = Math.max(50, currentSize + delta); // 最小50px
    
    // コンテナサイズを超えないように制限
    const maxSize = Math.min(containerData.width, containerData.height) * 0.9;
    const finalSize = Math.min(newSize, maxSize);
    
    // 中央を維持しながらサイズを変更
    const centerX = currentCropBoxData.left + currentCropBoxData.width / 2;
    const centerY = currentCropBoxData.top + currentCropBoxData.height / 2;
    
    const newLeft = centerX - finalSize / 2;
    const newTop = centerY - finalSize / 2;
    
    // 新しい位置がコンテナ内に収まるように調整
    const adjustedLeft = Math.max(0, Math.min(newLeft, containerData.width - finalSize));
    const adjustedTop = Math.max(0, Math.min(newTop, containerData.height - finalSize));
    
    cropper.setCropBoxData({
        left: adjustedLeft,
        top: adjustedTop,
        width: finalSize,
        height: finalSize
    });
}

// サイズ調整機能 - 正方形を維持しながらサイズを変更
function adjustCropSize(delta) {
    if (!cropper) return;
    
    const currentCropBoxData = cropper.getCropBoxData();
    const containerData = cropper.getContainerData();
    
    // 現在のサイズを取得
    const currentSize = Math.min(currentCropBoxData.width, currentCropBoxData.height);
    const newSize = Math.max(50, currentSize + delta); // 最小50px
    
    // コンテナサイズを超えないように制限
    const maxSize = Math.min(containerData.width, containerData.height) * 0.9;
    const finalSize = Math.min(newSize, maxSize);
    
    // 中央を維持しながらサイズを変更
    const centerX = currentCropBoxData.left + currentCropBoxData.width / 2;
    const centerY = currentCropBoxData.top + currentCropBoxData.height / 2;
    
    const newLeft = centerX - finalSize / 2;
    const newTop = centerY - finalSize / 2;
    
    // 新しい位置がコンテナ内に収まるように調整
    const adjustedLeft = Math.max(0, Math.min(newLeft, containerData.width - finalSize));
    const adjustedTop = Math.max(0, Math.min(newTop, containerData.height - finalSize));
    
    cropper.setCropBoxData({
        left: adjustedLeft,
        top: adjustedTop,
        width: finalSize,
        height: finalSize
    });
}

// 座標情報更新 - 実際のサイズを表示し、最終出力は640×640であることを明記
function updateCropInfo(cropData) {
    const x = Math.round(cropData.x);
    const y = Math.round(cropData.y);
    const width = Math.round(cropData.width);
    const height = Math.round(cropData.height);
    
    // 正方形のサイズ（小さい方の辺）
    const squareSize = Math.min(width, height);
    
    cropInfo.innerHTML = `選択範囲の左上位置: X=${x}, Y=${y} | 現在のサイズ: ${squareSize}×${squareSize}px | 最終出力: 640×640px`;
}

// リセット機能 - 画像表示をすべて初期化
function resetCrop() {
    if (cropper) {
        // Cropperを完全に初期化
        cropper.destroy();
        cropper = null;
        
        // 画像の表示を初期化（元のサイズと位置にリセット）
        sourceImage.style.transform = '';
        sourceImage.style.width = '';
        sourceImage.style.height = '';
        sourceImage.style.maxWidth = '';
        sourceImage.style.maxHeight = '';
        
        // 少し遅延を入れてからCropperを再初期化
        setTimeout(() => {
            initializeCropperSafely();
        }, 100);
        
        // プレビューキャンバスをクリア
        previewCtx.clearRect(0, 0, TARGET_WIDTH, TARGET_HEIGHT);
        
        // 座標情報を初期化
        cropInfo.innerHTML = '選択範囲の左上位置: X=0, Y=0 | 現在のサイズ: 0×0px | 最終出力: 640×640px';
        
        // 現在の画像ファイル名表示を更新
        updateCurrentImageDisplay();
        
        showTemporaryMessage('画像表示を初期化しました');
    }
}

// 中央配置 - 現在の選択範囲サイズを維持
function cropToCenter() {
    if (cropper) {
        // 現在の切り抜きボックスのサイズを保存
        const currentCropBoxData = cropper.getCropBoxData();
        const currentSize = Math.min(currentCropBoxData.width, currentCropBoxData.height);
        
        // コンテナの中央に現在のサイズで配置
        const containerData = cropper.getContainerData();
        const newLeft = (containerData.width - currentSize) / 2;
        const newTop = (containerData.height - currentSize) / 2;
        
        cropper.setCropBoxData({
            left: newLeft,
            top: newTop,
            width: currentSize,
            height: currentSize
        });
    }
}

// ホイールイベントを無効化する関数
function disableWheelZoom() {
    // Cropperコンテナが作成された後にイベントリスナーを追加
    setTimeout(() => {
        const cropperContainer = document.querySelector('.cropper-container');
        if (cropperContainer) {
            // ホイールイベントを preventDefault で無効化
            cropperContainer.addEventListener('wheel', function(e) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }, { passive: false });
            
            // タッチイベントによるピンチズームも無効化
            cropperContainer.addEventListener('touchstart', function(e) {
                if (e.touches.length > 1) {
                    e.preventDefault();
                }
            }, { passive: false });
            
            cropperContainer.addEventListener('touchmove', function(e) {
                if (e.touches.length > 1) {
                    e.preventDefault();
                }
            }, { passive: false });
            
            console.log('Wheel zoom disabled for cropper');
        }
    }, 200);
}

// 最初のCropper初期化後にホイールズーム無効化を適用
initializeCropperSafely();
disableWheelZoom();
