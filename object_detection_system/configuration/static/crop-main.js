/**
 * Crop Tool - Main file with initialization and utility functions
 * This file handles initialization and provides remaining utility functions
 * Most functionality has been moved to modular files
 */

// 一時的なメッセージ表示機能
function showTemporaryMessage(message, duration = 3000) {
    // 既存のメッセージがあれば削除
    const existingMsg = document.querySelector('.temporary-message');
    if (existingMsg) {
        existingMsg.remove();
    }

    // メッセージ要素を作成
    const messageDiv = document.createElement('div');
    messageDiv.className = 'temporary-message';
    messageDiv.textContent = message;
    
    // スタイルを設定
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #4CAF50;
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        z-index: 10000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        font-size: 14px;
        max-width: 300px;
        word-wrap: break-word;
    `;
    
    // ページに追加
    document.body.appendChild(messageDiv);
    
    // 指定時間後に削除
    setTimeout(() => {
        if (messageDiv && messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, duration);
}

// 現在の画像表示を更新
function updateCurrentImageDisplay() {
    const currentImageInfo = document.getElementById('current-image-info');
    const currentImageName = document.getElementById('current-image-name');
    
    console.log('updateCurrentImageDisplay called, selectedImagePath:', selectedImagePath);
    
    if (selectedImagePath && currentImageInfo && currentImageName) {
        const filename = selectedImagePath.split('/').pop();
        currentImageName.textContent = filename;
        currentImageInfo.style.display = 'block';
        console.log('Current image display updated:', filename);
    } else if (currentImageInfo) {
        currentImageInfo.style.display = 'none';
        console.log('Current image display hidden');
    }
}

// Cropperの制約を適用
function applyCropperConstraints() {
    if (!cropper) return;
    
    const container = document.querySelector('.cropper-container');
    if (container) {
        // コンテナサイズの制限
        container.style.maxWidth = '800px';
        container.style.maxHeight = '600px';
    }
}

// メイン初期化処理
document.addEventListener('DOMContentLoaded', function() {
    console.log('Crop tool initialized with modular structure');
    
    // プレビューキャンバスのサイズを設定
    previewCanvas.width = TARGET_WIDTH;
    previewCanvas.height = TARGET_HEIGHT;
    
    // 初期表示の更新
    updateCurrentImageDisplay();
    updateCoordinatesCount();
    
    // フォームのデフォルト動作を防止
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
        });
    }
    
    // 画像セクション内でのホイールイベントを制御
    const imageSection = document.querySelector('.image-section');
    if (imageSection) {
        imageSection.addEventListener('wheel', function(e) {
            // Cropperコンテナ内でのホイールイベントを無効化
            const cropperContainer = document.querySelector('.cropper-container');
            if (cropperContainer && cropperContainer.contains(e.target)) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        }, { passive: false });
    }
    
    // 画像コンテナ内でのホイールイベントを制御
    const imageContainer = document.querySelector('.image-container');
    if (imageContainer) {
        imageContainer.addEventListener('wheel', function(e) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }, { passive: false });
    }
});

// 画像読み込み時の処理
sourceImage.addEventListener('load', function() {
    console.log('Image loaded, initializing cropper...');
    
    // Cropperを安全に初期化
    initializeCropperSafely();
    
    // 現在の画像の座標を復元
    if (selectedImagePath) {
        loadImageCoordinates(selectedImagePath);
    }
    
    // 表示を更新
    updateCurrentImageDisplay();
    populateImageList(); // ナビゲーション用の画像リストを更新
});
