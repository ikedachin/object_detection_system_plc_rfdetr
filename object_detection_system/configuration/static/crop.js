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

// 画像選択モーダルを開く
function openImageSelector() {
    let imagePath;
    
    if (folderPathSelect.value === 'custom') {
        imagePath = customPathInput.value.trim();
    } else {
        imagePath = folderPathSelect.value;
    }
    
    if (!imagePath) {
        alert('画像パスを入力してください');
        return;
    }

    // モーダルを表示
    document.getElementById('image-modal').style.display = 'flex';
    
    // 画像一覧を取得
    fetch('/configuration/browse-images/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            path: imagePath
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayImageGrid(data.files, imagePath);
        } else {
            alert('エラー: ' + data.error);
            closeImageSelector();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('ファイル一覧の取得に失敗しました');
        closeImageSelector();
    });
}

// 画像グリッドを表示
function displayImageGrid(files, basePath) {
    const imageGrid = document.getElementById('image-grid');
    imageGrid.innerHTML = '';
    
    if (files.length === 0) {
        imageGrid.innerHTML = '<p style="text-align: center; color: #666;">画像ファイルが見つかりませんでした</p>';
        return;
    }
    
    files.forEach(file => {
        const imageItem = document.createElement('div');
        imageItem.className = 'image-item';
        // パスの正規化 - 末尾にスラッシュがない場合は追加
        const normalizedBasePath = basePath.endsWith('/') ? basePath : basePath + '/';
        const fullPath = normalizedBasePath + file;
        imageItem.onclick = () => selectImageFromGrid(fullPath, file, imageItem);
        
        const img = document.createElement('img');
        // Djangoの静的ファイル提供を利用
        img.src = `/${fullPath}`;
        img.alt = file;
        img.onerror = function() {
            this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwIiB5PSI1MCIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjEyIiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Tm8gSW1hZ2U8L3RleHQ+PC9zdmc+';
        };
        
        const imageName = document.createElement('div');
        imageName.className = 'image-name';
        imageName.textContent = file;
        
        imageItem.appendChild(img);
        imageItem.appendChild(imageName);
        imageGrid.appendChild(imageItem);
    });
}

// グリッドから画像を選択
function selectImageFromGrid(fullPath, filename, element) {
    // 他の選択を解除
    document.querySelectorAll('.image-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // 選択されたアイテムをハイライト
    element.classList.add('selected');
    
    // 選択された画像パスを保存
    selectedImagePath = fullPath;
    
    // 確認ボタンを有効化
    document.getElementById('confirm-btn').disabled = false;
    document.getElementById('confirm-btn').textContent = `選択: ${filename}`;
}

// 画像選択を確定
function confirmImageSelection() {
    if (!selectedImagePath) {
        alert('画像を選択してください');
        return;
    }
    
    // 選択された画像情報を表示
    const filename = selectedImagePath.split('/').pop();
    document.getElementById('selected-image-name').textContent = filename;
    document.getElementById('selected-image-info').style.display = 'flex';
    
    // モーダルを閉じる
    closeImageSelector();
    
    // 画像を実際に読み込み、ナビゲーション機能を有効化
    loadSelectedImage();
}

// モーダルを閉じる
function closeImageSelector() {
    document.getElementById('image-modal').style.display = 'none';
    document.getElementById('confirm-btn').disabled = true;
    document.getElementById('confirm-btn').textContent = '選択';
    
    // 選択状態をリセット
    document.querySelectorAll('.image-item').forEach(item => {
        item.classList.remove('selected');
    });
}

// 選択された画像を読み込み
function loadSelectedImage() {
    if (!selectedImagePath) {
        alert('画像を選択してください');
        return;
    }

    // 現在の画像の座標を保存（もし存在すれば）
    const previousImagePath = sourceImage.src;
    if (previousImagePath && previousImagePath !== `/${selectedImagePath}` && cropCoordinates.length > 0) {
        // 前の画像のパスを取得
        let prevPath = previousImagePath;
        if (prevPath.includes('/snaps/')) {
            const pathStart = prevPath.indexOf('/snaps/');
            prevPath = prevPath.substring(pathStart + 1);
        }
        if (prevPath && prevPath !== selectedImagePath) {
            saveCurrentImageCoordinates();
        }
    }

    // 画像のソースを更新（Djangoの静的ファイル提供を利用）
    sourceImage.src = `/${selectedImagePath}`;
    
    // 画像IDを更新（ファイル名から拡張子を除去）
    const imageId = selectedImagePath.split('/').pop().split('.')[0];
    document.getElementById('image-id').value = imageId;
    
    // 現在の画像ファイル名を表示
    updateCurrentImageDisplay();
    
    // 新しい画像の座標を復元
    loadImageCoordinates(selectedImagePath);
    
    // 画像ナビゲーションを更新（現在のフォルダの画像リストを取得）
    const pathParts = selectedImagePath.split('/');
    pathParts.pop(); // ファイル名を除去
    const folderPath = pathParts.join('/');
    if (folderPath) {
        updateImageList(folderPath);
    }
}

// タブ切り替え機能
function switchTab(tabName, event) {
    console.log('clicked')
    // タブボタンのアクティブ状態を切り替え
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    if (event && event.target) {
        event.target.classList.add('active');
    }

    // 選択方法の表示を切り替え
    document.querySelectorAll('.selection-method').forEach(method => {
        method.classList.remove('active');
    });
    document.getElementById(tabName + '-selection').classList.add('active');
}

// フォルダパス更新
function updateImagePath() {
    const selectedValue = folderPathSelect.value;
    if (selectedValue === 'custom') {
        customPathInput.style.display = 'inline-block';
        customPathInput.focus();
    } else {
        customPathInput.style.display = 'none';
        // 選択された画像情報をクリア
        document.getElementById('selected-image-info').style.display = 'none';
        selectedImagePath = null;
        
        // ナビゲーションを非表示
        document.getElementById('image-navigation').style.display = 'none';
        currentImageList = [];
        currentImageIndex = 0;
    }
}

// ファイルアップロード処理
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            uploadedImageData = e.target.result;
        };
        reader.readAsDataURL(file);
    } else {
        alert('画像ファイルを選択してください');
    }
}

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
        }
    });
}

// ページ読み込み完了時の初期化
document.addEventListener('DOMContentLoaded', function() {
    // 必要な初期化処理
    if (typeof updateSelectionMode === 'function') {
        updateSelectionMode(); // 初期選択モード反映
    }
    // 画像名表示も初期化
    if (typeof updateCurrentImageDisplay === 'function') {
        updateCurrentImageDisplay();
    }
    // 必要なら他の初期化もここで
});

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

// Cropper.js 初期化イベント
sourceImage.addEventListener('load', function() {
    initializeCropperSafely();
    // 画像読み込み完了時にファイル名表示を更新
    updateCurrentImageDisplay();
    
    // 画像読み込み完了時に座標を復元
    setTimeout(() => {
        if (selectedImagePath) {
            loadImageCoordinates(selectedImagePath);
        }
    }, 200);
});

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

// ウィンドウリサイズ時のイベントリスナー
window.addEventListener('resize', function() {
    enforceContainerLimits();
});

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

// 座標蓄積機能
function addCropCoordinate() {
    if (!cropper) {
        alert('画像を読み込んでください');
        return;
    }

    // 現在の切り抜きデータを取得（実際の画像座標）
    const cropData = cropper.getData(true);
    
    // 現在の画像ファイル名を取得
    let currentFileName = '不明';
    if (selectedImagePath) {
        currentFileName = selectedImagePath.split('/').pop();
    } else {
        // 画像のsrcから推測
        const imageSrc = sourceImage.src;
        if (imageSrc && imageSrc.includes('/snaps/')) {
            const pathParts = imageSrc.split('/');
            const filename = pathParts[pathParts.length - 1];
            if (filename && filename !== '') {
                currentFileName = filename;
            }
        }
    }
    
    // 正方形になるように調整（小さい方の辺に合わせる）
    const size = Math.min(cropData.width, cropData.height);
    const adjustedCropData = {
        id: ++coordinateCounter,
        x: Math.round(cropData.x),
        y: Math.round(cropData.y),
        width: Math.round(size),
        height: Math.round(size),
        fileName: currentFileName,
        imageId: document.getElementById('image-id').value
    };
    
    // 座標リストに追加
    cropCoordinates.push(adjustedCropData);
    
    // UIを更新
    updateCoordinatesList();
    updateCoordinatesCount();
    updateBoundingBoxDisplay(); // 包括座標表示も更新
    
    // ボタンの状態を更新
    document.getElementById('download-all-btn').disabled = false;
    document.getElementById('clear-all-btn').disabled = false;
    
    // 成功メッセージ
    showTemporaryMessage(`座標 #${adjustedCropData.id} を蓄積しました`);
}

// 座標リストのUI更新
function updateCoordinatesList() {
    const listElement = document.getElementById('coordinates-list');
    
    // 全ての画像の座標を取得
    const allCoordinates = getAllSavedCoordinatesWithCurrent();
    
    if (allCoordinates.length === 0) {
        listElement.innerHTML = '<p style="color: #666; text-align: center;">まだ座標が蓄積されていません</p>';
        return;
    }
    
    listElement.innerHTML = '';
    
    allCoordinates.forEach((coord, index) => {
        const item = document.createElement('div');
        item.className = 'coordinate-item';
        
        // 現在の画像の座標かどうかを判定
        const isCurrentImage = coord.imagePath === selectedImagePath;
        if (isCurrentImage) {
            item.classList.add('current-image-coordinate');
        }
        
        // ファイル名を短縮表示（長すぎる場合）
        const displayFileName = coord.fileName && coord.fileName.length > 20 
            ? coord.fileName.substring(0, 17) + '...' 
            : coord.fileName || '不明';
        
        item.innerHTML = `
            <div class="coordinate-info">
                <div class="coordinate-main">
                    #${coord.id}: X=${coord.x}, Y=${coord.y}, サイズ=${coord.width}×${coord.height}px
                    ${isCurrentImage ? '<span class="current-indicator">（現在の画像）</span>' : ''}
                </div>
                <div class="coordinate-filename" title="${coord.fileName || '不明'}">
                    📁 ${displayFileName}
                </div>
            </div>
            <div class="coordinate-actions">
                <button class="btn btn-secondary btn-small" onclick="previewCoordinate(${index}, '${coord.imagePath || ''}')">プレビュー</button>
                <button class="btn btn-secondary btn-small" onclick="removeCoordinate(${index}, '${coord.imagePath || ''}')">削除</button>
            </div>
        `;
        
        listElement.appendChild(item);
    });
}

// 座標数の表示更新
function updateCoordinatesCount() {
    const allCoordinates = getAllSavedCoordinatesWithCurrent();
    const currentImageCoords = cropCoordinates.length;
    
    let displayText = `現在の画像: ${currentImageCoords}個`;
    if (allCoordinates.length > currentImageCoords) {
        displayText += ` | 全体: ${allCoordinates.length}個`;
    }
    
    document.getElementById('coordinates-count').textContent = displayText;
    
    // 全体クリアボタンの状態を更新
    const clearAllImagesBtn = document.getElementById('clear-all-images-btn');
    if (clearAllImagesBtn) {
        clearAllImagesBtn.disabled = allCoordinates.length === 0;
    }
    
    // 一括ダウンロードボタンの状態を更新（全体の座標があれば有効）
    document.getElementById('download-all-btn').disabled = allCoordinates.length === 0;
}

// 特定の座標をプレビュー
function previewCoordinate(index, imagePath = '') {
    const allCoordinates = getAllSavedCoordinatesWithCurrent();
    
    if (index < 0 || index >= allCoordinates.length) return;
    
    const coord = allCoordinates[index];
    
    // 他の画像の座標の場合は、その画像に切り替える
    if (coord.imagePath && coord.imagePath !== selectedImagePath) {
        if (confirm(`座標をプレビューするために画像を "${coord.fileName}" に切り替えますか？`)) {
            // 現在の座標を保存
            if (selectedImagePath && cropCoordinates.length > 0) {
                saveCurrentImageCoordinates();
            }
            
            // 画像を切り替え
            selectedImagePath = coord.imagePath;
            sourceImage.src = `/${coord.imagePath}`;
            
            // 画像IDを更新
            const imageId = coord.fileName.split('.')[0];
            document.getElementById('image-id').value = imageId;
            
            // 表示を更新
            updateCurrentImageDisplay();
            
            // 新しい画像の座標を復元
            loadImageCoordinates(coord.imagePath);
            
            // 少し遅延してからプレビュー
            setTimeout(() => {
                if (cropper) {
                    cropper.setData({
                        x: coord.x,
                        y: coord.y,
                        width: coord.width,
                        height: coord.height
                    });
                }
                showTemporaryMessage(`座標 #${coord.id} (${coord.fileName || '不明'}) をプレビュー表示中`);
            }, 500);
        }
        return;
    }
    
    // 現在の画像の座標の場合は直接プレビュー
    if (cropper) {
        cropper.setData({
            x: coord.x,
            y: coord.y,
            width: coord.width,
            height: coord.height
        });
    }
    
    showTemporaryMessage(`座標 #${coord.id} (${coord.fileName || '不明'}) をプレビュー表示中`);
}

// 特定の座標を削除
function removeCoordinate(index, imagePath = '') {
    const allCoordinates = getAllSavedCoordinatesWithCurrent();
    
    if (index < 0 || index >= allCoordinates.length) return;
    
    const coord = allCoordinates[index];
    
    // 現在の画像の座標の場合
    if (coord.imagePath === selectedImagePath) {
        const currentIndex = cropCoordinates.findIndex(c => c.id === coord.id);
        if (currentIndex >= 0) {
            cropCoordinates.splice(currentIndex, 1);
        }
    } else {
        // 他の画像の座標の場合
        if (imageCoordinatesMap.has(coord.imagePath)) {
            const savedData = imageCoordinatesMap.get(coord.imagePath);
            const savedIndex = savedData.coordinates.findIndex(c => c.id === coord.id);
            if (savedIndex >= 0) {
                savedData.coordinates.splice(savedIndex, 1);
                
                // 座標がなくなった場合はその画像のエントリを削除
                if (savedData.coordinates.length === 0) {
                    imageCoordinatesMap.delete(coord.imagePath);
                }
            }
        }
    }
    
    updateCoordinatesList();
    updateCoordinatesCount();
    updateBoundingBoxDisplay();
    
    // 現在の画像の座標がなくなった場合はボタンを無効化
    if (cropCoordinates.length === 0) {
        document.getElementById('clear-all-btn').disabled = true;
    }
    
    showTemporaryMessage(`座標 #${coord.id} (${coord.fileName || '不明'}) を削除しました`);
}

// 現在の画像の座標をクリア
function clearAllCoordinates() {
    if (cropCoordinates.length === 0) {
        showTemporaryMessage('現在の画像にクリアする座標がありません');
        return;
    }
    
    if (confirm(`現在の画像の座標 ${cropCoordinates.length} 個を削除しますか？`)) {
        cropCoordinates = [];
        
        updateCoordinatesList();
        updateCoordinatesCount();
        updateBoundingBoxDisplay();
        
        document.getElementById('download-all-btn').disabled = true;
        document.getElementById('clear-all-btn').disabled = true;
        
        // 現在の画像の保存済み座標も削除
        if (selectedImagePath && imageCoordinatesMap.has(selectedImagePath)) {
            imageCoordinatesMap.delete(selectedImagePath);
        }
        
        showTemporaryMessage('現在の画像の座標をクリアしました');
    }
}

// 一括切り抜き実行
function downloadAllCrops() {
    const allCoordinates = getAllSavedCoordinatesWithCurrent();
    
    if (allCoordinates.length === 0) {
        alert('蓄積された座標がありません');
        return;
    }
    
    if (!confirm(`全ての画像の ${allCoordinates.length} 個の座標で一括切り抜きを実行しますか？`)) {
        return;
    }
    
    // 画像パスごとに座標をグループ化
    const coordinatesByImage = {};
    allCoordinates.forEach(coord => {
        const imagePath = coord.imagePath || selectedImagePath;
        if (!coordinatesByImage[imagePath]) {
            coordinatesByImage[imagePath] = [];
        }
        coordinatesByImage[imagePath].push(coord);
    });
    
    // 複数の画像がある場合は、各画像を個別に処理
    const processPromises = [];
    
    Object.keys(coordinatesByImage).forEach(imagePath => {
        const coords = coordinatesByImage[imagePath];
        
        processPromises.push(
            fetch('/configuration/process-batch-crop/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({
                    image_path: imagePath,
                    coordinates: coords
                })
            })
        );
    });
    
    // 全ての処理が完了するまで待機
    Promise.all(processPromises)
        .then(responses => {
            // 最初のレスポンスのZIPファイルをダウンロード（複数画像の場合は要改善）
            if (responses.length > 0 && responses[0].headers.get('content-type') === 'application/zip') {
                return responses[0].blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    const filename = responses[0].headers.get('content-disposition')?.split('filename=')[1]?.replace(/"/g, '') || 'cropped_images.zip';
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    showTemporaryMessage(`${allCoordinates.length} 個の座標を一括処理しました`);
                });
            } else {
                // JSONエラーレスポンスの場合
                return responses[0].json().then(data => {
                    alert('エラーが発生しました: ' + data.error);
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('一括処理中にエラーが発生しました');
        });
}

// 包括座標（すべての座標を含む最小矩形）を計算（現在の画像のみ）
function calculateBoundingBox() {
    if (cropCoordinates.length === 0) {
        return null;
    }
    
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    
    cropCoordinates.forEach(coord => {
        // 各座標の範囲を計算
        const x1 = coord.x;
        const y1 = coord.y;
        const x2 = coord.x + coord.width;
        const y2 = coord.y + coord.height;
        
        minX = Math.min(minX, x1);
        minY = Math.min(minY, y1);
        maxX = Math.max(maxX, x2);
        maxY = Math.max(maxY, y2);
    });
    
    return {
        x: Math.round(minX),
        y: Math.round(minY),
        width: Math.round(maxX - minX),
        height: Math.round(maxY - minY),
        right: Math.round(maxX),
        bottom: Math.round(maxY)
    };
}

// 全ての画像の座標を包括する矩形を計算
function calculateGlobalBoundingBox() {
    const allCoordinates = getAllSavedCoordinatesWithCurrent();
    
    if (allCoordinates.length === 0) {
        return null;
    }
    
    // 画像パスごとに座標をグループ化
    const coordinatesByImage = {};
    allCoordinates.forEach(coord => {
        const imagePath = coord.imagePath || selectedImagePath;
        if (!coordinatesByImage[imagePath]) {
            coordinatesByImage[imagePath] = [];
        }
        coordinatesByImage[imagePath].push(coord);
    });
    
    // 各画像の包括座標を計算し、さらにそれらを包括する座標を計算
    const imageBoundingBoxes = [];
    Object.keys(coordinatesByImage).forEach(imagePath => {
        const coords = coordinatesByImage[imagePath];
        if (coords.length === 0) return;
        
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;
        
        coords.forEach(coord => {
            const x1 = coord.x;
            const y1 = coord.y;
            const x2 = coord.x + coord.width;
            const y2 = coord.y + coord.height;
            
            minX = Math.min(minX, x1);
            minY = Math.min(minY, y1);
            maxX = Math.max(maxX, x2);
            maxY = Math.max(maxY, y2);
        });
        
        imageBoundingBoxes.push({
            imagePath: imagePath,
            fileName: imagePath.split('/').pop(),
            coordinates: coords.length,
            x: Math.round(minX),
            y: Math.round(minY),
            width: Math.round(maxX - minX),
            height: Math.round(maxY - minY),
            right: Math.round(maxX),
            bottom: Math.round(maxY)
        });
    });
    
    // 全ての画像の包括座標をさらに包括する座標を計算
    if (imageBoundingBoxes.length === 0) return null;
    
    let globalMinX = Infinity;
    let globalMinY = Infinity;
    let globalMaxX = -Infinity;
    let globalMaxY = -Infinity;
    
    imageBoundingBoxes.forEach(bbox => {
        globalMinX = Math.min(globalMinX, bbox.x);
        globalMinY = Math.min(globalMinY, bbox.y);
        globalMaxX = Math.max(globalMaxX, bbox.right);
        globalMaxY = Math.max(globalMaxY, bbox.bottom);
    });
    
    return {
        x: Math.round(globalMinX),
        y: Math.round(globalMinY),
        width: Math.round(globalMaxX - globalMinY),
        height: Math.round(globalMaxY - globalMinY),
        right: Math.round(globalMaxX),
        bottom: Math.round(globalMaxY),
        totalImages: imageBoundingBoxes.length,
        totalCoordinates: allCoordinates.length,
        imageDetails: imageBoundingBoxes
    };
}

// 全ての画像の座標を包括する最小矩形を計算
function calculateGlobalBoundingBox() {
    const allCoordinates = getAllSavedCoordinatesWithCurrent();
    
    if (allCoordinates.length === 0) {
        return null;
    }
    
    // 画像パスごとに座標をグループ化
    const coordinatesByImage = {};
    allCoordinates.forEach(coord => {
        const imagePath = coord.imagePath || selectedImagePath;
        if (!coordinatesByImage[imagePath]) {
            coordinatesByImage[imagePath] = [];
        }
        coordinatesByImage[imagePath].push(coord);
    });
    
    const globalBounds = [];
    
    // 各画像の包括座標を計算
    Object.keys(coordinatesByImage).forEach(imagePath => {
        const coords = coordinatesByImage[imagePath];
        
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;
        
        coords.forEach(coord => {
            const x1 = coord.x;
            const y1 = coord.y;
            const x2 = coord.x + coord.width;
            const y2 = coord.y + coord.height;
            
            minX = Math.min(minX, x1);
            minY = Math.min(minY, y1);
            maxX = Math.max(maxX, x2);
            maxY = Math.max(maxY, y2);
        });
        
        if (minX !== Infinity) {
            globalBounds.push({
                imagePath: imagePath,
                imageFileName: imagePath.split('/').pop(),
                x: Math.round(minX),
                y: Math.round(minY),
                width: Math.round(maxX - minX),
                height: Math.round(maxY - minY),
                right: Math.round(maxX),
                bottom: Math.round(maxY),
                coordinateCount: coords.length
            });
        }
    });
    
    return globalBounds;
}

// 包括座標の表示を更新
function updateBoundingBoxDisplay() {
    const boundingBoxSection = document.getElementById('bounding-box-section');
    const boundingBoxInfo = document.getElementById('bounding-box-info');
    
    // 現在の画像の包括座標
    const currentBbox = cropCoordinates.length >= 2 ? calculateBoundingBox() : null;
    
    // 全ての画像の包括座標
    const globalBounds = calculateGlobalBoundingBox();
    
    if (!currentBbox && (!globalBounds || globalBounds.totalImages === 0)) {
        boundingBoxSection.style.display = 'none';
        return;
    }
    
    let infoHtml = '';
    
    // 現在の画像の包括座標を表示
    if (currentBbox) {
        let currentFileName = '不明';
        if (selectedImagePath) {
            currentFileName = selectedImagePath.split('/').pop();
        } else {
            const imageSrc = sourceImage.src;
            if (imageSrc && imageSrc.includes('/snaps/')) {
                const pathParts = imageSrc.split('/');
                const filename = pathParts[pathParts.length - 1];
                if (filename && filename !== '') {
                    currentFileName = filename;
                }
            }
        }
        
        infoHtml += `
            <div class="bbox-section current-image-bbox">
                <h5>📍 現在の画像の包括座標</h5>
                <div><strong>画像:</strong> ${currentFileName}</div>
                <div><strong>座標範囲:</strong> X=${currentBbox.x}, Y=${currentBbox.y}</div>
                <div><strong>サイズ:</strong> ${currentBbox.width} × ${currentBbox.height} px</div>
                <div><strong>対象座標数:</strong> ${cropCoordinates.length}</div>
                <div class="bbox-buttons">
                    <button onclick="previewBoundingBox(${currentBbox.x}, ${currentBbox.y}, ${currentBbox.width}, ${currentBbox.height})" class="btn-preview">プレビュー</button>
                    <button onclick="saveBoundingBoxCrop()" class="btn-save">保存</button>
                </div>
            </div>
        `;
    }
    
    // 全ての画像の包括座標を表示
    if (globalBounds && globalBounds.totalImages > 0) {
        infoHtml += `
            <div class="bbox-section global-bbox">
                <h5>🌐 全体の包括座標</h5>
                <div><strong>対象画像数:</strong> ${globalBounds.totalImages}</div>
                <div><strong>総座標数:</strong> ${globalBounds.totalCoordinates}</div>
                <div><strong>全体座標範囲:</strong> X=${globalBounds.x}, Y=${globalBounds.y}</div>
                <div><strong>全体サイズ:</strong> ${globalBounds.width} × ${globalBounds.height} px</div>`;
        
        // 画像詳細を表示（複数画像がある場合）
        if (globalBounds.imageDetails.length > 1) {
            infoHtml += `
                <div class="global-details">
                    <details>
                        <summary>画像別詳細 (${globalBounds.imageDetails.length}画像)</summary>
                        <ul>`;
            globalBounds.imageDetails.forEach(detail => {
                infoHtml += `
                    <li>
                        <strong>${detail.fileName}</strong> (座標数: ${detail.coordinates})
                        <br>範囲: (${detail.x}, ${detail.y}) - (${detail.right}, ${detail.bottom})
                        <br>サイズ: ${detail.width} × ${detail.height} px
                    </li>`;
            });
            infoHtml += `
                        </ul>
                    </details>
                </div>`;
        }
        
        infoHtml += `
                <div class="bbox-buttons">
                    <button onclick="saveGlobalBoundingBoxYaml()" class="btn-save">YAML保存</button>
                    <button onclick="exportAllCropsWithGlobalBbox()" class="btn-download">一括切り抜き</button>
                </div>
            </div>
        `;
    }
    
    if (infoHtml) {
        boundingBoxInfo.innerHTML = infoHtml;
        boundingBoxSection.style.display = 'block';
    } else {
        boundingBoxSection.style.display = 'none';
    }
}

// 包括座標をプレビュー表示
function previewBoundingBox() {
    if (!cropper || cropCoordinates.length < 2) {
        alert('包括座標を計算するには2個以上の座標が必要です');
        return;
    }
    
    const bbox = calculateBoundingBox();
    if (!bbox) {
        alert('包括座標の計算に失敗しました');
        return;
    }
    
    // Cropperの選択範囲を包括座標に設定
    cropper.setData({
        x: bbox.x,
        y: bbox.y,
        width: bbox.width,
        height: bbox.height
    });
    
    showTemporaryMessage(`包括座標をプレビュー表示中 (${bbox.width}×${bbox.height}px)`);
}

// 包括座標をYAMLファイルに保存
function saveBoundingBoxToYaml() {
    if (cropCoordinates.length < 2) {
        alert('包括座標を保存するには2個以上の座標が必要です');
        return;
    }
    
    const bbox = calculateBoundingBox();
    if (!bbox) {
        alert('包括座標の計算に失敗しました');
        return;
    }
    
    // 現在の画像情報を取得
    let currentFileName = '不明';
    let imagePath = '';
    
    if (selectedImagePath) {
        currentFileName = selectedImagePath.split('/').pop();
        imagePath = selectedImagePath;
    } else {
        const imageSrc = sourceImage.src;
        if (imageSrc && imageSrc.includes('/snaps/')) {
            currentFileName = imageSrc.split('/').pop();
            const pathStart = imageSrc.indexOf('/snaps/');
            imagePath = imageSrc.substring(pathStart);
        }
    }
    
    if (!confirm(`包括座標をYAMLファイルに保存しますか？\n\n画像: ${currentFileName}\n座標: (${bbox.x}, ${bbox.y}) サイズ: ${bbox.width}×${bbox.height}px`)) {
        return;
    }
    
    // バックエンドにYAML保存リクエストを送信
    fetch('/configuration/save-bounding-box-yaml/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            image_path: imagePath,
            image_filename: currentFileName,
            bounding_box: bbox,
            individual_coordinates: cropCoordinates,
            total_coordinates: cropCoordinates.length
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showTemporaryMessage(`YAMLファイルに保存しました: ${data.filename}`);
        } else {
            alert('保存に失敗しました: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('YAML保存中にエラーが発生しました');
    });
}

// 全体の包括座標をYAMLで保存
function saveGlobalBoundingBoxYaml() {
    const globalBounds = calculateGlobalBoundingBox();
    
    if (!globalBounds || globalBounds.totalImages === 0) {
        alert('保存する座標がありません');
        return;
    }
    
    if (!confirm(`全体の包括座標をYAMLファイルに保存しますか？\n\n対象画像数: ${globalBounds.totalImages}\n総座標数: ${globalBounds.totalCoordinates}\n全体サイズ: ${globalBounds.width}×${globalBounds.height}px`)) {
        return;
    }
    
    // バックエンドに全体包括座標のYAML保存リクエストを送信
    fetch('/configuration/save-global-bounding-box-yaml/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            global_bounding_box: globalBounds,
            all_coordinates: getAllSavedCoordinatesWithCurrent()
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showTemporaryMessage(`全体包括座標をYAMLファイルに保存しました: ${data.filename}`);
        } else {
            alert('保存に失敗しました: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('全体包括座標のYAML保存中にエラーが発生しました');
    });
}

// 全体包括座標での一括切り抜き
function exportAllCropsWithGlobalBbox() {
    const globalBounds = calculateGlobalBoundingBox();
    
    if (!globalBounds || globalBounds.totalImages === 0) {
        alert('切り抜きする座標がありません');
        return;
    }
    
    if (!confirm(`全ての画像の座標を包括する範囲で一括切り抜きを実行しますか？\n\n対象画像数: ${globalBounds.totalImages}\n切り抜きサイズ: ${globalBounds.width}×${globalBounds.height}px`)) {
        return;
    }
    
    // 各画像に全体包括座標を適用して切り抜き
    const cropRequests = globalBounds.imageDetails.map(imageDetail => ({
        image_path: imageDetail.imagePath,
        crop_data: {
            x: globalBounds.x,
            y: globalBounds.y,
            width: globalBounds.width,
            height: globalBounds.height
        }
    }));
    
    // バックエンドに全体包括座標での一括切り抜きリクエストを送信
    fetch('/configuration/export-global-bbox-crops/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            crop_requests: cropRequests,
            global_bounding_box: globalBounds
        })
    })
    .then(response => {
        if (response.headers.get('Content-Type').includes('application/zip')) {
            return response.blob();
        } else {
            return response.json();
        }
    })
    .then(data => {
        if (data instanceof Blob) {
            // ZIPファイルのダウンロード
            const url = window.URL.createObjectURL(data);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `global_bbox_crops_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            showTemporaryMessage(`全体包括座標での一括切り抜きが完了しました (${globalBounds.totalImages}画像)`);
        } else if (data.success) {
            showTemporaryMessage(`全体包括座標での一括切り抜きが完了しました: ${data.filename}`);
        } else {
            alert('切り抜きに失敗しました: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('全体包括座標での一括切り抜き中にエラーが発生しました');
    });
}

// 全ての保存済み座標を取得（現在の画像の座標も含む）
function getAllSavedCoordinatesWithCurrent() {
    const allCoords = [];
    
    // 保存済みの他の画像の座標を追加
    imageCoordinatesMap.forEach((data, imagePath) => {
        // 現在の画像の場合はスキップ（後で現在の座標を追加するため）
        if (imagePath !== selectedImagePath) {
            data.coordinates.forEach(coord => {
                allCoords.push({
                    ...coord,
                    imagePath: imagePath
                });
            });
        }
    });
    
    // 現在の画像の座標を追加
    cropCoordinates.forEach(coord => {
        allCoords.push({
            ...coord,
            imagePath: selectedImagePath
        });
    });
    
    // ID順にソート
    allCoords.sort((a, b) => a.id - b.id);
    
    return allCoords;
}

// --- プロジェクト名から画像フォルダ選択機能 ---
let projectFoldersData = {};

function updateSelectionMode() {
    const selectionMode = document.getElementById('selection-mode').value;
    const predefinedSelection = document.getElementById('predefined-selection');
    const projectSelection = document.getElementById('project-selection');
    const customSelection = document.getElementById('custom-selection');
    // 全ての選択エリアを非表示
    predefinedSelection.style.display = 'none';
    projectSelection.style.display = 'none';
    customSelection.style.display = 'none';
    // 選択されたモードに応じて表示
    switch (selectionMode) {
        case 'predefined':
            predefinedSelection.style.display = 'block';
            break;
        case 'project':
            projectSelection.style.display = 'block';
            loadProjectFolders();
            break;
        case 'custom':
            customSelection.style.display = 'block';
            break;
    }
    clearSelectedImageInfo();
}

function loadProjectFolders() {
    fetch('/configuration/get-project-image-folders/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            projectFoldersData = data.folders;
            populateProjectSelect();
        } else {
            alert('プロジェクトフォルダの取得に失敗しました: ' + data.error);
        }
    })
    .catch(error => {
        alert('プロジェクトフォルダの取得中にエラーが発生しました');
    });
}

function populateProjectSelect() {
    const projectSelect = document.getElementById('project-name');
    projectSelect.innerHTML = '<option value="">プロジェクトを選択してください...</option>';
    for (const [projectKey, projectInfo] of Object.entries(projectFoldersData)) {
        const option = document.createElement('option');
        option.value = projectKey;
        option.textContent = projectInfo.name;
        projectSelect.appendChild(option);
    }
}

function updateProjectFolders() {
    const projectName = document.getElementById('project-name').value;
    const projectFolderContainer = document.getElementById('project-folder-container');
    const projectFolderSelect = document.getElementById('project-folder');
    if (!projectName || !projectFoldersData[projectName]) {
        projectFolderContainer.style.display = 'none';
        return;
    }
    projectFolderSelect.innerHTML = '<option value="">フォルダを選択してください...</option>';
    const projectInfo = projectFoldersData[projectName];
    projectInfo.subfolders.forEach(folder => {
        const option = document.createElement('option');
        option.value = folder.path;
        option.textContent = `${folder.name} (${folder.image_count}枚)`;
        projectFolderSelect.appendChild(option);
    });
    projectFolderContainer.style.display = 'block';
    clearSelectedImageInfo();
}

function updateProjectPath() {
    const projectFolder = document.getElementById('project-folder').value;
    if (projectFolder) {
        selectedFolderPath = projectFolder;
        clearSelectedImageInfo();
        const navigation = document.getElementById('image-navigation');
        if (navigation) navigation.style.display = 'none';
        currentImageList = [];
        currentImageIndex = 0;
    }
}

function getCurrentFolderPath() {
    const selectionMode = document.getElementById('selection-mode').value;
    switch (selectionMode) {
        case 'predefined':
            return document.getElementById('folder-path').value;
        case 'project':
            return document.getElementById('project-folder').value;
        case 'custom':
            return document.getElementById('custom-path').value.trim();
        default:
            return '';
    }
}

function clearSelectedImageInfo() {
    const selectedImageInfo = document.getElementById('selected-image-info');
    if (selectedImageInfo) selectedImageInfo.style.display = 'none';
    selectedImagePath = null;
    const sourceImage = document.getElementById('source-image');
    if (sourceImage) sourceImage.src = '';
    if (cropper) { cropper.destroy(); cropper = null; }
}

// 現在の画像表示を更新
function updateCurrentImageDisplay() {
    const currentImageInfo = document.getElementById('current-image-info');
    const currentImageName = document.getElementById('current-image-name');
    if (!currentImageInfo || !currentImageName) return;
    if (selectedImagePath) {
        const name = selectedImagePath.split('/').pop();
        currentImageName.textContent = name;
        currentImageInfo.style.display = 'block';
    } else {
        currentImageName.textContent = '未選択';
        currentImageInfo.style.display = 'none';
    }
}
