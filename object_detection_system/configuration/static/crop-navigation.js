// crop-navigation.js - 画像ナビゲーション関連の機能

// 画像ナビゲーション関数
function loadPreviousImage() {
    console.log('loadPreviousImage called');
    console.log('currentImageList:', currentImageList);
    console.log('currentImageIndex:', currentImageIndex);
    console.log('selectedImagePath:', selectedImagePath);
    
    if (currentImageList.length === 0) {
        alert('画像リストが空です。まず画像を選択してください。');
        return;
    }
    
    if (currentImageIndex > 0) {
        currentImageIndex--;
        const previousImagePath = currentImageList[currentImageIndex];
        const previousImageName = previousImagePath.split('/').pop();
        
        console.log('Moving to previous image:', previousImagePath);
        
        // selectImageFromGrid関数を使わずに直接画像を読み込む
        selectedImagePath = previousImagePath;
        loadSelectedImage();
        updateImageNavigation();
    } else {
        alert('これ以上前の画像はありません');
    }
}

function loadNextImage() {
    console.log('loadNextImage called');
    console.log('currentImageList:', currentImageList);
    console.log('currentImageIndex:', currentImageIndex);
    console.log('selectedImagePath:', selectedImagePath);
    
    if (currentImageList.length === 0) {
        alert('画像リストが空です。まず画像を選択してください。');
        return;
    }
    
    if (currentImageIndex < currentImageList.length - 1) {
        currentImageIndex++;
        const nextImagePath = currentImageList[currentImageIndex];
        const nextImageName = nextImagePath.split('/').pop();
        
        console.log('Moving to next image:', nextImagePath);
        
        // selectImageFromGrid関数を使わずに直接画像を読み込む
        selectedImagePath = nextImagePath;
        loadSelectedImage();
        updateImageNavigation();
    } else {
        alert('これ以上次の画像はありません');
    }
}

function updateImageNavigation() {
    const prevBtn = document.getElementById('prev-image-btn');
    const nextBtn = document.getElementById('next-image-btn');
    const counter = document.getElementById('image-counter');
    const navigation = document.getElementById('image-navigation');
    
    console.log('updateImageNavigation called');
    console.log('currentImageList.length:', currentImageList.length);
    console.log('currentImageIndex:', currentImageIndex);
    console.log('selectedImagePath:', selectedImagePath);
    
    if (!navigation || !prevBtn || !nextBtn || !counter) {
        console.error('Navigation elements not found');
        return;
    }
    
    // 画像が選択されている場合はナビゲーションを表示
    if (selectedImagePath && currentImageList.length > 0) {
        // ナビゲーションを表示
        navigation.style.display = 'flex';
        
        // ボタンの有効/無効状態を更新
        prevBtn.disabled = currentImageIndex === 0;
        nextBtn.disabled = currentImageIndex === currentImageList.length - 1;
        
        // カウンターを更新
        counter.textContent = `${currentImageIndex + 1} / ${currentImageList.length}`;
        
        console.log('Navigation updated - prev disabled:', prevBtn.disabled, 'next disabled:', nextBtn.disabled);
        console.log('Counter updated:', counter.textContent);
    } else {
        // 画像が選択されていないか、リストが空の場合は非表示
        navigation.style.display = 'none';
        console.log('Navigation hidden - no image selected or empty list');
    }
}

// 指定されたフォルダの画像リストを更新
function updateImageList(folderPath) {
    // サーバーから画像リストを取得
    fetch('/configuration/browse-images/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            path: folderPath
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 画像リストを更新
            currentImageList = data.files.map(file => {
                const normalizedBasePath = folderPath.endsWith('/') ? folderPath : folderPath + '/';
                return normalizedBasePath + file;
            });
            
            // 現在の画像のインデックスを見つける
            if (selectedImagePath) {
                currentImageIndex = currentImageList.indexOf(selectedImagePath);
                if (currentImageIndex === -1) {
                    currentImageIndex = 0;
                }
            } else {
                currentImageIndex = 0;
            }
            
            currentBasePath = folderPath;
            
            // ナビゲーションUIを更新
            updateImageNavigation();
            
            console.log(`Image list updated: ${currentImageList.length} images found`);
            console.log(`Current image index: ${currentImageIndex}, path: ${selectedImagePath}`);
        } else {
            console.error('Failed to update image list:', data.error);
        }
    })
    .catch(error => {
        console.error('Error updating image list:', error);
    });
}

// 画像リストを自動的に生成（現在の画像から推測）
function populateImageList() {
    if (!selectedImagePath) return;
    
    const pathParts = selectedImagePath.split('/');
    pathParts.pop(); // ファイル名を除去
    const folderPath = pathParts.join('/');
    
    if (folderPath && folderPath !== currentBasePath) {
        updateImageList(folderPath);
    }
}

// ショートカットキー処理
document.addEventListener('keydown', function(event) {
    if (event.ctrlKey && event.key === 'ArrowLeft') {
        // Navigate to the previous image
        loadPreviousImage();
    } else if (event.ctrlKey && event.key === 'ArrowRight') {
        // Navigate to the next image
        loadNextImage();
    } else if (event.key === ' ') {
        // Accumulate coordinates
        event.preventDefault(); // Prevent default spacebar scrolling
        addCropCoordinate();
    } else if (event.key === 'Escape') {
        closeImageSelector();
    } else if (event.key === 'Enter') {
        // Confirm image selection in modal
        confirmImageSelection();
    }
});
