// crop-image-selector.js - 画像選択とモーダル関連の機能

// 画像選択モーダルを開く
function openImageSelector() {
    let imagePath;
    
    // 新しいプロジェクト選択機能からパスを取得
    if (typeof getCurrentFolderPath === 'function') {
        imagePath = getCurrentFolderPath();
    } else {
        // 従来の方法（後方互換性）
        if (folderPathSelect.value === 'custom') {
            imagePath = customPathInput.value.trim();
        } else {
            imagePath = folderPathSelect.value;
        }
    }
    
    if (!imagePath) {
        alert('画像パスを選択または入力してください');
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
            populateImageList(data.files.map(file => `${imagePath}/${file}`));
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

    console.log('loadSelectedImage called with:', selectedImagePath);

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
        console.log('Updating image list for folder:', folderPath);
        updateImageList(folderPath);
    } else {
        // フォルダパスがない場合でも、現在の画像でナビゲーションを表示
        console.log('No folder path, updating navigation with current image only');
        currentImageList = [selectedImagePath];
        currentImageIndex = 0;
        updateImageNavigation();
    }
}

// 画像リストを作成
function populateImageList(imagePaths) {
    // 文字列の配列として統一
    currentImageList = imagePaths.slice(); // コピーを作成
    currentImageIndex = 0; // Reset to the first image
    updateImageNavigation();
    
    console.log('populateImageList called with:', imagePaths);
    console.log('currentImageList set to:', currentImageList);
}

// タブ切り替え機能
function switchTab(tabName) {
    // タブボタンのアクティブ状態を切り替え
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

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
            sourceImage.src = uploadedImageData;
            
            // アップロードされた画像の情報を設定
            const filename = file.name;
            const imageId = filename.split('.')[0];
            document.getElementById('image-id').value = imageId;
            
            // ナビゲーション情報をクリア
            currentImageList = [];
            currentImageIndex = 0;
            document.getElementById('image-navigation').style.display = 'none';
            
            showTemporaryMessage(`画像 "${filename}" をアップロードしました`);
        };
        reader.readAsDataURL(file);
    } else {
        alert('画像ファイルを選択してください');
    }
}
