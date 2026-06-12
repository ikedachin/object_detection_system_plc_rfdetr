// crop-coordinates.js - 座標管理関連の機能

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
        showTemporaryMessage('現在表示中にクリアする座標がありません');
        return;
    }
    
    if (confirm(`現在表示中の座標 ${cropCoordinates.length} 個を削除しますか？\n（他の画像の座標は保持されます）`)) {
        // 現在表示中の座標のみをクリア（保存済みの座標は残す）
        cropCoordinates = [];
        
        updateCoordinatesList();
        updateCoordinatesCount();
        updateBoundingBoxDisplay();
        
        // ボタンの状態を更新（現在表示中の座標がないため無効化）
        document.getElementById('clear-all-btn').disabled = true;
        
        // 他の画像に座標が保存されているかチェックして download-all-btn の状態を決定
        const allSavedCoords = getAllSavedCoordinatesWithCurrent();
        document.getElementById('download-all-btn').disabled = allSavedCoords.length === 0;
        
        showTemporaryMessage('現在表示中の座標をクリアしました（他の画像の座標は保持されています）');
    }
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

// 現在の画像の座標を保存（画像切り替え時）
function saveCurrentImageCoordinates() {
    if (!selectedImagePath || cropCoordinates.length === 0) {
        return;
    }
    
    // 座標データを深くコピーして保存
    const coordinatesCopy = cropCoordinates.map(coord => ({ ...coord }));
    
    imageCoordinatesMap.set(selectedImagePath, {
        coordinates: coordinatesCopy,
        savedAt: new Date().toISOString()
    });
    
    console.log(`Saved ${coordinatesCopy.length} coordinates for image: ${selectedImagePath}`);
}

// 画像の座標を読み込み（画像切り替え時）
function loadImageCoordinates(imagePath) {
    if (!imagePath) {
        cropCoordinates = [];
        updateCoordinatesList();
        updateCoordinatesCount();
        return;
    }
    
    if (imageCoordinatesMap.has(imagePath)) {
        const savedData = imageCoordinatesMap.get(imagePath);
        // 座標データを深くコピーして復元
        cropCoordinates = savedData.coordinates.map(coord => ({ ...coord }));
        
        console.log(`Loaded ${cropCoordinates.length} coordinates for image: ${imagePath}`);
    } else {
        // 保存された座標がない場合は空にする
        cropCoordinates = [];
    }
    
    // UIを更新
    updateCoordinatesList();
    updateCoordinatesCount();
    updateBoundingBoxDisplay();
    
    // ボタンの状態を更新
    const hasCoords = cropCoordinates.length > 0;
    document.getElementById('download-all-btn').disabled = !hasCoords;
    document.getElementById('clear-all-btn').disabled = !hasCoords;
}

// 全ての画像の座標をクリア
function clearAllImagesCoordinates() {
    const totalCoords = getAllSavedCoordinatesWithCurrent().length;
    
    if (totalCoords === 0) {
        showTemporaryMessage('クリアする座標がありません');
        return;
    }
    
    if (confirm(`全ての画像の座標 ${totalCoords} 個を削除しますか？`)) {
        // 現在の画像の座標をクリア
        cropCoordinates = [];
        
        // 保存された座標をすべてクリア
        imageCoordinatesMap.clear();
        
        // UIを更新
        updateCoordinatesList();
        updateCoordinatesCount();
        updateBoundingBoxDisplay();
        
        // ボタンの状態を更新
        document.getElementById('download-all-btn').disabled = true;
        document.getElementById('clear-all-btn').disabled = true;
        
        showTemporaryMessage('全ての画像の座標をクリアしました');
    }
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
    
    if (globalBounds.length === 0) return null;
    
    // 全ての画像の包括座標をさらに包括する座標を計算
    let globalMinX = Infinity;
    let globalMinY = Infinity;
    let globalMaxX = -Infinity;
    let globalMaxY = -Infinity;
    
    globalBounds.forEach(bbox => {
        globalMinX = Math.min(globalMinX, bbox.x);
        globalMinY = Math.min(globalMinY, bbox.y);
        globalMaxX = Math.max(globalMaxX, bbox.right);
        globalMaxY = Math.max(globalMaxY, bbox.bottom);
    });
    
    return {
        x: Math.round(globalMinX),
        y: Math.round(globalMinY),
        width: Math.round(globalMaxX - globalMinX),
        height: Math.round(globalMaxY - globalMinY),
        right: Math.round(globalMaxX),
        bottom: Math.round(globalMaxY),
        totalImages: globalBounds.length,
        totalCoordinates: allCoordinates.length,
        imageDetails: globalBounds
    };
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
        if (boundingBoxSection) boundingBoxSection.style.display = 'none';
        return;
    }
    
    let infoHtml = '';
    
    // 現在の画像の包括座標を表示
    if (currentBbox) {
        let currentFileName = '不明';
        if (selectedImagePath) {
            currentFileName = selectedImagePath.split('/').pop();
        }
        
        infoHtml += `
            <div class="bbox-section current-image-bbox">
                <h5>📍 現在の画像の包括座標</h5>
                <div><strong>画像:</strong> ${currentFileName}</div>
                <div><strong>座標範囲:</strong> X=${currentBbox.x}, Y=${currentBbox.y}</div>
                <div><strong>サイズ:</strong> ${currentBbox.width} × ${currentBbox.height} px</div>
                <div><strong>対象座標数:</strong> ${cropCoordinates.length}</div>
                <div class="bbox-buttons">
                    <button onclick="previewBoundingBox()" class="btn-preview">プレビュー</button>
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
                <div><strong>全体サイズ:</strong> ${globalBounds.width} × ${globalBounds.height} px</div>
            </div>
        `;
    }
    
    if (infoHtml && boundingBoxInfo) {
        boundingBoxInfo.innerHTML = infoHtml;
        if (boundingBoxSection) boundingBoxSection.style.display = 'block';
    } else if (boundingBoxSection) {
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
