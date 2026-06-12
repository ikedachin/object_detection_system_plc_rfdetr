/**
 * Export and Download Functionality for Crop Tool
 * Handles YAML export, batch downloads, and global bounding box operations
 */

// 一括切り抜き実行（包括座標でフォルダ内全画像を処理）
function downloadAllCrops() {
    const allCoordinates = getAllSavedCoordinatesWithCurrent();
    
    if (allCoordinates.length === 0) {
        alert('蓄積された座標がありません');
        return;
    }
    
    // 包括座標を計算
    const globalBounds = calculateGlobalBoundingBox();
    
    if (!globalBounds || globalBounds.totalImages === 0) {
        alert('包括座標を計算できませんでした');
        return;
    }
    
    // 現在選択されているフォルダパスを取得
    let currentFolderPath;
    
    // 新しいプロジェクト選択機能からパスを取得
    if (typeof getCurrentFolderPath === 'function') {
        currentFolderPath = getCurrentFolderPath();
    } else {
        // 従来の方法（後方互換性）
        const folderPathSelect = document.getElementById('folder-path');
        if (folderPathSelect.value === 'custom') {
            currentFolderPath = document.getElementById('custom-path').value.trim();
        } else {
            currentFolderPath = folderPathSelect.value;
        }
    }
    
    if (!currentFolderPath) {
        alert('フォルダパスが選択されていません');
        return;
    }
    
    if (!confirm(`フォルダ内の全ての画像を包括座標で一括切り抜きを実行しますか？\n\n包括座標: X=${globalBounds.x}, Y=${globalBounds.y}\nサイズ: ${globalBounds.width}×${globalBounds.height}px\n対象フォルダ: ${currentFolderPath}`)) {
        return;
    }
    
    // フォルダ内の全画像を取得して包括座標で切り抜き
    downloadAllImagesWithBoundingBox(currentFolderPath, globalBounds);
}

// 単一座標での切り抜き処理
function processSingleCrop(imagePath, coord) {
    return new Promise((resolve) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        
        img.onload = function() {
            try {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // 640x640の正方形で出力
                canvas.width = TARGET_WIDTH;
                canvas.height = TARGET_HEIGHT;
                
                // 切り抜き範囲を計算
                const sourceX = coord.x;
                const sourceY = coord.y;
                const sourceSize = Math.min(coord.width, coord.height);
                
                // 白い背景で塗りつぶし
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, TARGET_WIDTH, TARGET_HEIGHT);
                
                // 画像を描画（リサイズ）
                ctx.drawImage(
                    img,
                    sourceX, sourceY, sourceSize, sourceSize,
                    0, 0, TARGET_WIDTH, TARGET_HEIGHT
                );
                
                // データURLを生成
                const dataURL = canvas.toDataURL('image/png');
                const filename = `crop_${coord.fileName}_${coord.id}.png`;
                
                resolve({
                    success: true,
                    dataURL: dataURL,
                    filename: filename,
                    coordinate: coord
                });
            } catch (error) {
                console.error('Crop processing error:', error);
                resolve({
                    success: false,
                    error: error.message,
                    coordinate: coord
                });
            }
        };
        
        img.onerror = function() {
            resolve({
                success: false,
                error: 'Image load failed',
                coordinate: coord
            });
        };
        
        // 画像を読み込み
        img.src = `/${imagePath}`;
    });
}

// ZIPファイルとしてダウンロード
function downloadAsZip(results, totalCount) {
    // JSZipライブラリを使用してZIPファイルを作成
    const zip = new JSZip();
    
    results.forEach(result => {
        // データURLからバイナリデータに変換
        const base64Data = result.dataURL.split(',')[1];
        zip.file(result.filename, base64Data, {base64: true});
    });
    
    // ZIPファイルを生成してダウンロード
    zip.generateAsync({type: 'blob'})
        .then(function(content) {
            const url = URL.createObjectURL(content);
            const a = document.createElement('a');
            a.href = url;
            a.download = `crops_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showTemporaryMessage(`一括切り抜きが完了しました (${results.length}/${totalCount}個)`);
        })
        .catch(function(error) {
            console.error('ZIP generation error:', error);
            alert('ZIPファイルの生成に失敗しました');
        });
}

// 座標をYAMLファイルに保存
function saveCoordinatesYaml() {
    if (cropCoordinates.length === 0) {
        alert('保存する座標がありません');
        return;
    }
    
    const imageId = document.getElementById('image-id').value || 'unknown';
    
    if (!confirm(`${cropCoordinates.length} 個の座標をYAMLファイルに保存しますか？`)) {
        return;
    }
    
    // バックエンドにYAML保存リクエストを送信
    fetch('/configuration/save-coordinates-yaml/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            coordinates: cropCoordinates,
            image_id: imageId,
            image_path: selectedImagePath
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showTemporaryMessage(`座標をYAMLファイルに保存しました: ${data.filename}`);
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
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showTemporaryMessage(`全体包括座標をYAMLファイルに保存しました: ${data.filename}`);
        } else {
            alert('保存に失敗しました: ' + (data.error || '不明なエラー'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (error.message.includes('404')) {
            alert('YAML保存機能はまだ実装されていません。バックエンドのエンドポイントが必要です。');
        } else {
            alert('全体包括座標のYAML保存中にエラーが発生しました: ' + error.message);
        }
    });
}


// フォルダ内の全画像を包括座標で切り抜き
function downloadAllImagesWithBoundingBox(folderPath, globalBounds) {
    // まずフォルダ内の全ての画像ファイルを取得
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
        if (!data.success) {
            alert('フォルダ内の画像取得に失敗しました: ' + data.error);
            return;
        }
        
        if (data.files.length === 0) {
            alert('フォルダ内に画像ファイルが見つかりませんでした');
            return;
        }
        
        // 各画像を包括座標で切り抜き
        const processPromises = data.files.map(filename => {
            const normalizedFolderPath = folderPath.endsWith('/') ? folderPath : folderPath + '/';
            const fullImagePath = normalizedFolderPath + filename;
            
            return processSingleCropWithBoundingBox(fullImagePath, filename, globalBounds);
        });
        
        // 全ての処理を並行実行
        Promise.all(processPromises)
            .then(results => {
                // 成功した結果のみをフィルタ
                const successResults = results.filter(result => result.success);
                
                if (successResults.length === 0) {
                    alert('切り抜きに失敗しました');
                    return;
                }
                
                // ZIPファイルとしてダウンロード
                downloadAsZip(successResults, data.files.length);
                
                showTemporaryMessage(`${successResults.length}/${data.files.length} の画像を包括座標で切り抜きました`);
            })
            .catch(error => {
                console.error('Batch crop error:', error);
                alert('一括切り抜き中にエラーが発生しました');
            });
    })
    .catch(error => {
        console.error('Error:', error);
        alert('フォルダ内の画像取得に失敗しました');
    });
}

// 包括座標を使用した単一画像の切り抜き処理
function processSingleCropWithBoundingBox(imagePath, filename, globalBounds) {
    return new Promise((resolve) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        
        img.onload = function() {
            try {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // 640x640の正方形で出力
                canvas.width = TARGET_WIDTH;
                canvas.height = TARGET_HEIGHT;
                
                // 包括座標を使用
                const sourceX = globalBounds.x;
                const sourceY = globalBounds.y;
                const sourceWidth = globalBounds.width;
                const sourceHeight = globalBounds.height;
                
                // 白い背景で塗りつぶし
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, TARGET_WIDTH, TARGET_HEIGHT);
                
                // 画像のサイズチェック
                if (sourceX + sourceWidth > img.width || sourceY + sourceHeight > img.height) {
                    console.warn(`Image ${filename} is smaller than bounding box. Adjusting...`);
                    
                    // 画像サイズに合わせて調整
                    const adjustedWidth = Math.min(sourceWidth, img.width - sourceX);
                    const adjustedHeight = Math.min(sourceHeight, img.height - sourceY);
                    const adjustedX = Math.max(0, Math.min(sourceX, img.width - adjustedWidth));
                    const adjustedY = Math.max(0, Math.min(sourceY, img.height - adjustedHeight));
                    
                    // 調整された範囲で描画
                    ctx.drawImage(
                        img,
                        adjustedX, adjustedY, adjustedWidth, adjustedHeight,
                        0, 0, TARGET_WIDTH, TARGET_HEIGHT
                    );
                } else {
                    // 正常な範囲で描画
                    ctx.drawImage(
                        img,
                        sourceX, sourceY, sourceWidth, sourceHeight,
                        0, 0, TARGET_WIDTH, TARGET_HEIGHT
                    );
                }
                
                // データURLを生成
                const dataURL = canvas.toDataURL('image/png');
                const outputFilename = `crop_bbox_${filename.replace(/\.[^/.]+$/, '')}.png`;
                
                resolve({
                    success: true,
                    dataURL: dataURL,
                    filename: outputFilename,
                    originalFilename: filename
                });
            } catch (error) {
                console.error('Crop processing error:', error);
                resolve({
                    success: false,
                    error: error.message,
                    originalFilename: filename
                });
            }
        };
        
        img.onerror = function() {
            resolve({
                success: false,
                error: 'Image load failed',
                originalFilename: filename
            });
        };
        
        // 画像を読み込み
        img.src = `/${imagePath}`;
    });
}

// 現在の画像の包括座標をYAMLファイルに保存
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
    }
    
    if (!confirm(`現在の画像の包括座標をYAMLファイルに保存しますか？\n\n画像: ${currentFileName}\n座標: X=${bbox.x}, Y=${bbox.y}\nサイズ: ${bbox.width}×${bbox.height}px\n対象座標数: ${cropCoordinates.length}`)) {
        return;
    }
    
    // バックエンドに包括座標のYAML保存リクエストを送信
    fetch('/configuration/save-bounding-box-yaml/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            bounding_box: bbox,
            coordinates: cropCoordinates,
            // image_filename: currentFileName,
            // image_path: imagePath,
            // image_id: document.getElementById('image-id').value || 'unknown'
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showTemporaryMessage(`包括座標をYAMLファイルに保存しました: ${data.filename}`);
        } else {
            alert('保存に失敗しました: ' + (data.error || '不明なエラー'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (error.message.includes('404')) {
            alert('YAML保存機能はまだ実装されていません。バックエンドのエンドポイントが必要です。');
        } else {
            alert('包括座標のYAML保存中にエラーが発生しました: ' + error.message);
        }
    });
}
