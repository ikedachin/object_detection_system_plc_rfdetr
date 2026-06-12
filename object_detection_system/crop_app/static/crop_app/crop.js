// crop.js - シンプルな画像切り抜きアプリ

let cropper = null;
let imageList = [];
let imageIndex = 0;
let cropCoords = [];
let currentProject = null;
let currentFolder = null;
let allProjects = [];

const sourceImage = document.getElementById('source-image');
const cropInfo = document.getElementById('crop-info');
const TARGET_SIZE = 640;

// プロジェクト読み込み状況を更新
function updateProjectStatus(status, message, isError = false) {
    const statusText = document.getElementById('project-status-text');
    const debugInfo = document.getElementById('project-debug-info');
    
    if (statusText) {
        statusText.textContent = status;
        statusText.className = `badge ${isError ? 'bg-danger' : 'bg-primary'}`;
    }
    
    if (debugInfo && message) {
        debugInfo.innerHTML = message;
        debugInfo.style.display = 'block';
    }
}

// デバッグ情報を画面に表示
function showDebugInfo() {
    const debugInfo = document.getElementById('project-debug-info');
    if (!debugInfo) return;
    
    const info = `
        <strong>デバッグ情報:</strong><br>
        • allProjects: ${typeof allProjects !== 'undefined' ? `${allProjects.length}個` : '未定義'}<br>
        • currentProject: ${typeof currentProject !== 'undefined' && currentProject ? currentProject.name : '未選択'}<br>
        • currentFolder: ${typeof currentFolder !== 'undefined' && currentFolder ? currentFolder : '未選択'}<br>
        • loadProjects関数: ${typeof loadProjects === 'function' ? '利用可能' : '未定義'}
    `;
    
    debugInfo.innerHTML = info;
    debugInfo.style.display = 'block';
}

// プロジェクト一覧を読み込み
function loadProjects() {
    console.log('loadProjects関数実行開始');
    updateProjectStatus('読み込み中...', 'プロジェクト一覧を取得しています...');
    
    const projectSelect = document.getElementById('project-name');
    if (!projectSelect) {
        console.error('プロジェクトセレクターが見つかりません');
        updateProjectStatus('エラー', 'プロジェクトセレクターが見つかりません', true);
        return;
    }
    
    // 読み込み中の表示
    projectSelect.innerHTML = '<option value="">プロジェクト読み込み中...</option>';
    projectSelect.disabled = true;
    
    fetch('/crop_app/api/get-projects-list/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => {
        console.log('プロジェクト読み込みレスポンス:', response.status, response.statusText);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('プロジェクト読み込み成功:', data);
        
        if (data.success) {
            allProjects = data.projects || [];
            console.log('プロジェクト数:', allProjects.length);
            updateProjectStatus(`${allProjects.length}個読み込み完了`, `${allProjects.length}個のプロジェクトが見つかりました`);
            updateProjectSelector();
            showDebugInfo();
        } else {
            console.error('プロジェクト読み込みエラー:', data.error);
            updateProjectStatus('読み込み失敗', `エラー: ${data.error || '不明なエラー'}`, true);
            showProjectError('プロジェクト読み込みエラー: ' + (data.error || '不明なエラー'));
        }
    })
    .catch(error => {
        console.error('プロジェクト読み込み通信エラー:', error);
        updateProjectStatus('通信エラー', `通信エラー: ${error.message}`, true);
        showProjectError('通信エラー: ' + error.message);
    })
    .finally(() => {
        projectSelect.disabled = false;
    });
}

// プロジェクト読み込みエラーを表示
function showProjectError(message) {
    const projectSelect = document.getElementById('project-name');
    if (projectSelect) {
        projectSelect.innerHTML = '<option value="">プロジェクト読み込み失敗</option>';
    }
    
    const projectInfoDisplay = document.getElementById('project-info-display');
    if (projectInfoDisplay) {
        projectInfoDisplay.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> ${message}
                <br>
                <button class="btn btn-sm btn-outline-danger mt-2" onclick="loadProjects()">
                    <i class="bi bi-arrow-clockwise"></i> 再読み込み
                </button>
            </div>
        `;
        projectInfoDisplay.style.display = 'block';
    }
}

// プロジェクトセレクターを更新
function updateProjectSelector() {
    const projectSelect = document.getElementById('project-name');
    if (!projectSelect) {
        console.error('プロジェクトセレクターが見つかりません');
        return;
    }
    
    console.log('プロジェクトセレクター更新開始。プロジェクト数:', allProjects.length);
    
    // セレクターをクリア
    projectSelect.innerHTML = '<option value="">プロジェクトを選択してください...</option>';
    
    // プロジェクトが存在しない場合
    if (!allProjects || allProjects.length === 0) {
        const noProjectOption = document.createElement('option');
        noProjectOption.value = '';
        noProjectOption.textContent = 'プロジェクトが見つかりません';
        noProjectOption.disabled = true;
        projectSelect.appendChild(noProjectOption);
        
        console.log('プロジェクトが見つかりません');
        return;
    }
    
    // プロジェクトオプションを追加
    allProjects.forEach((project, index) => {
        console.log(`プロジェクト ${index + 1}:`, project);
        
        const option = document.createElement('option');
        option.value = project.id;
        
        // プロジェクト表示名を構築
        const displayText = `${project.name} (${project.created_at})`;
        option.textContent = displayText;
        
        // アクティブプロジェクトの強調表示
        if (project.is_active) {
            option.style.fontWeight = 'bold';
            option.style.color = '#0d6efd';
            option.style.backgroundColor = '#e7f3ff';
            option.selected = true; // アクティブプロジェクトを自動選択
        }
        
        projectSelect.appendChild(option);
    });
    
    console.log('プロジェクトセレクター更新完了');
    
    // // 最初のプロジェクトを自動選択（オプション）
    // if (allProjects.length > 0) {
    //     const firstActiveProject = allProjects.find(p => p.is_active);
    //     if (firstActiveProject) {
    //         projectSelect.value = firstActiveProject.id;
    //         console.log('アクティブプロジェクトを自動選択:', firstActiveProject.name);
    //         // プロジェクト選択を実行
    //         setTimeout(() => updateProjectFolders(), 100);
    //     }
    // }
}

// プロジェクト選択時の処理
function updateProjectFolders() {
    const projectSelect = document.getElementById('project-name');
    const folderContainer = document.getElementById('project-folder-container');
    const folderSelect = document.getElementById('project-folder');
    const projectInfoDisplay = document.getElementById('project-info-display');
    
    if (!projectSelect || !folderContainer || !folderSelect) {
        console.error('必要な要素が見つかりません');
        return;
    }
    
    const projectId = projectSelect.value;
    console.log('プロジェクト選択:', projectId);
    
    if (!projectId) {
        folderContainer.style.display = 'none';
        projectInfoDisplay.style.display = 'none';
        currentProject = null;
        return;
    }
    
    // 選択されたプロジェクト情報を取得
    currentProject = allProjects.find(p => p.id == projectId);
    if (!currentProject) {
        console.error('プロジェクトが見つかりません:', projectId);
        return;
    }
    
    console.log('選択されたプロジェクト:', currentProject);
    
    // プロジェクト情報を表示
    displayProjectInfo(currentProject);
    
    // フォルダ読み込み中の表示
    folderSelect.innerHTML = '<option value="">フォルダ読み込み中...</option>';
    folderSelect.disabled = true;
    
    // 自動選択状況を表示
    updateAutoSelectionStatus('フォルダ検索中...', 'data_collectionフォルダを探しています...', 'info');
    
    // フォルダ一覧を取得
    fetch('/crop_app/api/get-project-folders/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ project_id: projectId })
    })
    .then(response => {
        // レスポンスの内容をPromiseとしてではなく、実際のJSONとして出力
        response.clone().json().then(json => {
            console.log('全レスポンス(JSON):', json);
        }).catch(e => {
            console.warn('JSONパース失敗:', e);
        });

        console.log('フォルダ読み込みレスポンス:', response.status, response.ok);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('フォルダ読み込み成功:', data);
        
        if (data.success) {
            updateFolderSelector(data.folders);
            folderContainer.style.display = 'block';
        } else {
            console.error('フォルダ読み込みエラー:', data.error);
            folderContainer.style.display = 'none';
            showFolderError('フォルダ読み込みエラー: ' + (data.error || '不明なエラー'));
        }
    })
    .catch(error => {
        console.error('フォルダ読み込み通信エラー:', error);
        folderContainer.style.display = 'none';
        showFolderError('通信エラー: ' + error.message);
    })
    .finally(() => {
        folderSelect.disabled = false;
    });
}

// 自動選択状況を更新
function updateAutoSelectionStatus(status, detail, type = 'info') {
    const statusText = document.getElementById('auto-selection-text');
    const statusDetail = document.getElementById('auto-selection-detail');
    const statusContainer = document.getElementById('auto-selection-status');
    
    if (statusText) {
        statusText.textContent = status;
        statusText.className = `ms-2 badge bg-${type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info'}`;
    }
    
    if (statusDetail && detail) {
        statusDetail.innerHTML = detail;
    }
    
    if (statusContainer) {
        statusContainer.style.display = 'block';
        
        // 5秒後にフェードアウト（成功時のみ）
        if (type === 'success') {
            setTimeout(() => {
                if (statusContainer) {
                    statusContainer.style.opacity = '0.7';
                }
            }, 5000);
        }
    }
}

// data_collection関連の警告を表示
function showDataCollectionWarning(message) {
    const projectInfoDisplay = document.getElementById('project-info-display');
    if (projectInfoDisplay) {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'alert alert-info mt-2';
        warningDiv.innerHTML = `
            <i class="bi bi-info-circle"></i> <strong>自動選択情報:</strong><br>
            ${message}
        `;
        projectInfoDisplay.appendChild(warningDiv);
        
        // 5秒後に自動で削除
        setTimeout(() => {
            if (warningDiv.parentElement) {
                warningDiv.remove();
            }
        }, 5000);
    }
}

// フォルダ読み込みエラーを表示
function showFolderError(message) {
    const folderSelect = document.getElementById('project-folder');
    if (folderSelect) {
        folderSelect.innerHTML = '<option value="">フォルダ読み込み失敗</option>';
    }
    
    const projectInfoDisplay = document.getElementById('project-info-display');
    if (projectInfoDisplay) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-warning mt-2';
        errorDiv.innerHTML = `
            <i class="bi bi-exclamation-triangle"></i> ${message}
            <br>
            <button class="btn btn-sm btn-outline-warning mt-2" onclick="updateProjectFolders()">
                <i class="bi bi-arrow-clockwise"></i> フォルダ再読み込み
            </button>
        `;
        projectInfoDisplay.appendChild(errorDiv);
    }
}

// プロジェクト情報を表示
function displayProjectInfo(project) {
    const projectInfoDisplay = document.getElementById('project-info-display');
    if (!projectInfoDisplay) return;
    
    const totalImages = project.folders ? project.folders.reduce((sum, folder) => sum + folder.image_count, 0) : 0;
    const description = project.description || '';  // descriptionが存在しない場合は空文字列
    
    projectInfoDisplay.innerHTML = `
        <div class="row">
            <div class="col-6">
                <small class="text-muted">プロジェクト名:</small><br>
                <strong class="text-info">${project.name}</strong>
            </div>
            <div class="col-6">
                <small class="text-muted">作成日:</small><br>
                <span class="text-secondary">${project.created_at}</span>
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-6">
                <small class="text-muted">フォルダ数:</small><br>
                <span class="badge bg-primary">${project.folders ? project.folders.length : 0}個</span>
            </div>
            <div class="col-6">
                <small class="text-muted">総画像数:</small><br>
                <span class="badge bg-success">${totalImages}枚</span>
            </div>
        </div>
        ${description ? `
        <div class="mt-2">
            <small class="text-muted">説明:</small><br>
            <small class="text-secondary">${description}</small>
        </div>
        ` : ''}
    `;
    
    projectInfoDisplay.style.display = 'block';
}

// フォルダセレクターを更新
function updateFolderSelector(folders) {
    const folderSelect = document.getElementById('project-folder');
    if (!folderSelect) {
        console.error('フォルダセレクターが見つかりません');
        return;
    }
    
    console.log('フォルダセレクター更新開始。フォルダ数:', folders.length);
    
    // セレクターをクリア
    folderSelect.innerHTML = '<option value="">フォルダを選択してください...</option>';
    
    // フォルダが存在しない場合
    if (!folders || folders.length === 0) {
        const noFolderOption = document.createElement('option');
        noFolderOption.value = '';
        noFolderOption.textContent = 'フォルダが見つかりません';
        noFolderOption.disabled = true;
        folderSelect.appendChild(noFolderOption);
        
        console.log('フォルダが見つかりません');
        return;
    }
    
    // フォルダオプションを追加
    folders.forEach((folder, index) => {
        console.log(`フォルダ ${index + 1}:`, folder);
        
        const option = document.createElement('option');
        option.value = folder.path;
        option.textContent = `${folder.name} (${folder.image_count}枚)`;

        // 画像数が多いフォルダを強調表示
        if (folder.image_count > 0) {
            option.style.fontWeight = 'normal';
        } else {
            option.style.color = '#6c757d';
            option.style.fontStyle = 'italic';
        }
        
        folderSelect.appendChild(option);
    });
    
    console.log('フォルダセレクター更新完了');
    
    // data_collectionフォルダを優先的に自動選択
    if (folders.length > 0) {
        // まずdata_collectionフォルダを探す
        const dataCollectionFolder = folders.find(folder => 
            folder.name.toLowerCase() === 'data_collection' || 
            folder.path.toLowerCase().includes('data_collection')
        );
        
        if (dataCollectionFolder && dataCollectionFolder.image_count > 0) {
            folderSelect.value = dataCollectionFolder.path;
            console.log('data_collectionフォルダを自動選択:', dataCollectionFolder.name, '画像数:', dataCollectionFolder.image_count);
            
            // 自動選択状況を表示
            updateAutoSelectionStatus(
                'data_collectionを選択',
                `✓ data_collectionフォルダを見つけました (${dataCollectionFolder.image_count}枚の画像)`,
                'success'
            );
            
            // フォルダ選択を実行
            setTimeout(() => updateProjectPath(), 100);
        } else if (dataCollectionFolder && dataCollectionFolder.image_count === 0) {
            // data_collectionはあるが画像がない場合
            console.warn('data_collectionフォルダが見つかりましたが、画像がありません');
            
            // 他のフォルダで画像があるものを選択
            const bestFolder = folders.filter(f => f.image_count > 0).reduce((prev, current) => 
                (current.image_count > prev.image_count) ? current : prev, null
            );
            
            if (bestFolder) {
                folderSelect.value = bestFolder.path;
                console.log('代替フォルダを自動選択:', bestFolder.name, '画像数:', bestFolder.image_count);
                
                // 自動選択状況を表示
                updateAutoSelectionStatus(
                    '代替フォルダを選択',
                    `⚠ data_collectionに画像がないため、${bestFolder.name}を選択 (${bestFolder.image_count}枚)`,
                    'warning'
                );
                
                setTimeout(() => updateProjectPath(), 100);
            }
        } else {
            // data_collectionが見つからない場合
            console.warn('data_collectionフォルダが見つかりません');
            
            // 画像が最も多いフォルダを選択
            const bestFolder = folders.reduce((prev, current) => 
                (current.image_count > prev.image_count) ? current : prev
            );
            
            if (bestFolder && bestFolder.image_count > 0) {
                folderSelect.value = bestFolder.path;
                console.log('最適フォルダを自動選択:', bestFolder.name, '画像数:', bestFolder.image_count);
                
                // 自動選択状況を表示
                updateAutoSelectionStatus(
                    '最適フォルダを選択',
                    `ℹ data_collectionが見つからないため、${bestFolder.name}を選択 (${bestFolder.image_count}枚)`,
                    'info'
                );
                
                // フォルダ選択を実行
                setTimeout(() => updateProjectPath(), 100);
            }
        }
    }
}

// プロジェクトフォルダ選択時の処理
function updateProjectPath() {
    const folderSelect = document.getElementById('project-folder');
    if (!folderSelect) {
        console.error('フォルダセレクターが見つかりません');
        return;
    }
    
    const folderPath = folderSelect.value;
    console.log('フォルダ選択:', folderPath);
    
    if (!folderPath) {
        currentFolder = null;
        console.log('フォルダ選択がクリアされました');
        return;
    }
    
    currentFolder = folderPath;
    console.log('現在のフォルダ設定:', currentFolder);
    
    // 選択されたフォルダの画像を読み込み
    console.log('画像読み込み開始...');
    loadImages(folderPath);
}

// 選択モード更新
function updateSelectionMode() {
    const selectionMode = document.getElementById('selection-mode').value;
    const predefinedSelection = document.getElementById('predefined-selection');
    const projectSelection = document.getElementById('project-selection');
    const customSelection = document.getElementById('custom-selection');
    
    // 全て非表示
    predefinedSelection.style.display = 'none';
    projectSelection.style.display = 'none';
    customSelection.style.display = 'none';
    
    // 選択されたモードのみ表示
    switch(selectionMode) {
        case 'predefined':
            predefinedSelection.style.display = 'block';
            break;
        case 'project':
            projectSelection.style.display = 'block';
            break;
        case 'custom':
            customSelection.style.display = 'block';
            break;
    }
}

// 画像パス更新（定義済みパス用）
function updateImagePath() {
    const folderPath = document.getElementById('folder-path').value;
    if (folderPath) {
        loadImages(folderPath);
    }
}

/**
 * 指定したパスの画像リストを取得し、最初の画像を表示する。
 * @param {string} path - 画像フォルダのパス
 */
function loadImages(path) {
    if (!path) {
        console.warn('パスが指定されていません');
        showImageError('パスが指定されていません');
        return;
    }

    console.log('画像リスト取得開始:', path);

    // ナビゲーション非表示（画像クリアは後で実施）
    const imageNavigation = document.getElementById('image-navigation');
    if (imageNavigation) imageNavigation.style.display = 'none';

    // CSRFトークン取得
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!csrfToken) {
        showImageError('CSRFトークンが取得できません');
        return;
    }

    const debugtime = new Date().toISOString();
    console.log(`[DEBUG ${debugtime}] 画像リスト取得リクエスト:`, path);
    fetch('/crop_app/browse-images/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ path })
    })
    .then(response => {
        console.log('画像リスト取得レスポンス:', response.status);
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        return response.json();
    })
    .then(data => {
        if (data.success) {
            imageList = Array.isArray(data.files) ? data.files : [];
            imageIndex = 0;
            updateImageNavigation();
            if (imageList.length > 0) {
                showImage();
                updateCurrentImageInfo();
                const folderName = currentFolder ? currentFolder.split(/[/\\]/).pop() : 'フォルダ';
                showImageSuccess(`${imageList.length}枚の画像を読み込みました (${folderName}フォルダ)`);
                updateAutoSelectionStatus(
                    '画像読み込み完了',
                    `✓ ${folderName}フォルダから${imageList.length}枚の画像を読み込みました`,
                    'success'
                );
            } else {
                clearImageDisplay();
                showImageWarning('このフォルダに画像ファイルが見つかりませんでした');
            }
        } else {
            console.error('画像リスト取得エラー:', data.error);
            showImageError('画像リスト取得エラー: ' + (data.error || '不明なエラー'));
        }
    })
    .catch(error => {
        console.error('画像リスト取得通信エラー:', error);
        showImageError('通信エラー: ' + error.message);
    });
}

// 画像エラー表示
function showImageError(message) {
    const imageContainer = document.getElementById('image-container');
    if (imageContainer) {
        // 既存のエラーメッセージを削除
        const oldError = document.getElementById('image-error-message');
        if (oldError) oldError.remove();
        // エラーメッセージ要素を作成
        const errorDiv = document.createElement('div');
        errorDiv.id = 'image-error-message';
        errorDiv.className = 'alert alert-danger m-3';
        errorDiv.innerHTML = `
            <i class="bi bi-exclamation-triangle"></i> ${message}
            ${currentProject ? `<div class="mt-2">
                <small class="text-muted">デバッグ情報:</small><br>
                <small>プロジェクト: ${currentProject.name}</small><br>
                <small>フォルダ: ${currentFolder || 'なし'}</small><br>
                <small>画像: ${imageList[imageIndex] || 'なし'}</small><br>
                <small>画像インデックス: ${imageIndex}/${imageList.length}</small>
            </div>` : ''}
            <br>
            <div class="mt-2">
                <button class="btn btn-sm btn-outline-danger me-2" onclick="retryLoadImages()">
                    <i class="bi bi-arrow-clockwise"></i> 再試行
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="skipToNextImage()">
                    <i class="bi bi-skip-forward"></i> 次の画像
                </button>
            </div>
        `;
        imageContainer.appendChild(errorDiv);
        imageContainer.classList.add('no-image');
    }
}

// 次の画像にスキップ
function skipToNextImage() {
    if (imageIndex < imageList.length - 1) {
        imageIndex++;
        showImage();
        updateImageNavigation();
    } else {
        showImageWarning('これが最後の画像です');
    }
}

// 画像警告表示
function showImageWarning(message) {
    const imageContainer = document.getElementById('image-container');
    if (imageContainer) {
        // 既存のエラーメッセージを削除
        const oldError = document.getElementById('image-error-message');
        if (oldError) oldError.remove();
        // 警告メッセージ要素を作成
        const warnDiv = document.createElement('div');
        warnDiv.id = 'image-error-message';
        warnDiv.className = 'alert alert-warning m-3';
        warnDiv.innerHTML = `
            <i class="bi bi-info-circle"></i> ${message}
        `;
        imageContainer.appendChild(warnDiv);
        imageContainer.classList.add('no-image');
    }
}

// 画像成功表示
function showImageSuccess(message) {
    const currentImageInfo = document.getElementById('current-image-info');
    if (currentImageInfo) {
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success alert-dismissible fade show mt-2';
        successDiv.innerHTML = `
            <i class="bi bi-check-circle"></i> ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        currentImageInfo.appendChild(successDiv);
        
        // 3秒後に自動で削除
        setTimeout(() => {
            if (successDiv.parentElement) {
                successDiv.remove();
            }
        }, 3000);
    }
}

// 画像再読み込み
function retryLoadImages() {
    const currentPath = getCurrentPath();
    if (currentPath) {
        loadImages(currentPath);
    } else {
        console.error('再読み込み用のパスが見つかりません');
    }
}

function showImage() {
    console.log('showImage関数実行開始');
    if (!imageList.length) {
        console.warn('画像リストが空です');
        return;
    }
    // パス検証
    if (currentFolder && currentProject && !validateProjectImagePath()) {
        showImageError('プロジェクト画像パスの検証に失敗しました');
        return;
    }
    const currentPath = getCurrentPath();
    console.log('getCurrentPath()の返り値:', currentPath);
    if (!currentPath && !currentFolder) {
        console.error('現在のパスが取得できません');
        showImageError('画像パスが設定されていません');
        return;
    }
    // 画像パスを生成
    let imageSrc = `${currentPath}/${imageList[imageIndex]}`;
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] DEBUG: imageSrc初期値`, imageSrc);
    if (currentFolder && currentProject) {
        const folderName = currentFolder.split(/[/\\]/).pop();
        imageSrc = `/crop_app/api/get-project-image/?project=${encodeURIComponent(currentProject.name)}&folder=${encodeURIComponent(folderName)}&image=${encodeURIComponent(imageList[imageIndex])}`;
        console.log('プロジェクト画像パス生成:', {
            project: currentProject.name,
            folder: folderName,
            image: imageList[imageIndex],
            fullPath: imageSrc
        });
    } else {
        imageSrc = `/crop_app/api/get-static-image/?path=${encodeURIComponent(currentPath)}&image=${encodeURIComponent(imageList[imageIndex])}`;
        console.log('静的画像パス生成:', {
            path: currentPath,
            image: imageList[imageIndex],
            fullPath: imageSrc
        });
    }
    // sourceImage要素の存在確認
    if (!sourceImage) {
        console.error('sourceImage要素が取得できていません');
        return;
    } else {
        console.log('sourceImage要素取得OK:', sourceImage);
    }
    // srcセット直前のログ
    console.log('sourceImage.srcにセットするURL:', imageSrc);
    let thisImageIndex = imageIndex;
    sourceImage.onload = () => {
        if (thisImageIndex !== imageIndex) {
            console.log('onload: 表示中の画像インデックスが変化したため処理をスキップ');
            return;
        }
        // 画像正常時はno-imageクラスを必ず除去
        const imageContainer = document.getElementById('image-container');
        if (imageContainer) imageContainer.classList.remove('no-image');
        // cropper-activeクラスを必ず除去（imgを表示するため）
        if (imageContainer) imageContainer.classList.remove('cropper-active');
        // 画像を必ず表示（display/visibilityはCSSに任せる）
        // initializeCropperを呼び出す
        initializeCropper();
    };
    sourceImage.onerror = () => {
        console.error('画像onerror発火:', imageSrc);
        console.error('エラー詳細:', {
            currentProject: currentProject,
            currentFolder: currentFolder,
            imageIndex: imageIndex,
            imageList: imageList,
            imageFile: imageList[imageIndex]
        });
    };
    sourceImage.src = imageSrc;
}

// Cropperの描画エリアをcolの横幅に合わせてリサイズ
function syncCropperBoxSizes() {
    // CSSのmax-width:800px, width:100%に一元化したため、JSでのピクセル指定は不要
    // 必要ならCropperのresize/relayoutを促すだけ
    if (cropper) {
        cropper.reset(); // 画像サイズや親要素変更時にリセット
        cropper.resize && cropper.resize(); // Cropper.js v2以降ならresize()も
    }
    // デバッグ用ログ
    const imageContainer = document.getElementById('image-container');
    const cropperContainer = imageContainer ? imageContainer.querySelector('.cropper-container') : null;
    const canvas = cropperContainer ? cropperContainer.querySelector('.cropper-canvas') : null;
    const wrapBox = cropperContainer ? cropperContainer.querySelector('.cropper-wrap-box') : null;
    console.log('syncCropperBoxSizes実行:', {
        imageContainer: imageContainer ? `${imageContainer.offsetWidth}x${imageContainer.offsetHeight}` : 'なし',
        cropperContainer: cropperContainer ? `${cropperContainer.offsetWidth}x${cropperContainer.offsetHeight}` : 'なし',
        canvas: canvas ? `${canvas.offsetWidth}x${canvas.offsetHeight}` : 'なし',
        wrapBox: wrapBox ? `${wrapBox.offsetWidth}x${wrapBox.offsetHeight}` : 'なし',
    });
}

function resizeCropperToCol() {
    // 画像とCropperの幅は100%、高さはautoに統一
    const imageContainer = document.getElementById('image-container');
    const sourceImage = document.getElementById('source-image');
    if (!imageContainer || !sourceImage) return;
    sourceImage.style.width = '100%';
    sourceImage.style.height = 'auto';
    // Cropperのcanvasもリサイズ
    if (cropper) {
        setTimeout(syncCropperBoxSizes, 100);
    }
}

function initializeCropper() {
    if (typeof Cropper === 'undefined') {
        console.error('Cropper.js が読み込まれていません');
        return;
    }
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
    const imageContainer = document.getElementById('image-container');
    imageContainer.classList.add('cropper-active');
    const sourceImage = document.getElementById('source-image');
    if (!sourceImage) {
        console.error('sourceImage要素が見つかりません');
        return;
    }
    // 画像の幅は100%、高さauto
    sourceImage.style.width = '100%';
    sourceImage.style.height = 'auto';
    // Cropper初期化
    cropper = new Cropper(sourceImage, {
        aspectRatio: 1,
        viewMode: 1,
        autoCropArea: 0.6,
        responsive: true, // 明示
        restore: true,
        guides: true,
        center: true,
        highlight: true,
        cropBoxMovable: true,
        cropBoxResizable: true,
        toggleDragModeOnDblclick: false,
        zoomable: false,
        wheelZoomRatio: 0,
        crop(event) {
            updateCropInfo(event.detail);
        }
    });
    // Cropperコンテナでのマウスホイールによるズームを完全に無効化
    const cropperContainer = imageContainer.querySelector('.cropper-container');
    if (cropperContainer) {
        cropperContainer.style.boxSizing = 'border-box';
        cropperContainer.addEventListener('wheel', function(e) {
            e.preventDefault();
        }, { passive: false });
    }
    setTimeout(syncCropperBoxSizes, 100);
    // 初期化後にリサイズ
    resizeCropperToCol();
}

// ウィンドウリサイズ時にもCropperをリサイズ
window.addEventListener('resize', function() {
    resizeCropperToCol();
});

// 画像表示をクリア
function clearImageDisplay() {
    const sourceImage = document.getElementById('source-image');
    const imageContainer = document.getElementById('image-container');
    if (sourceImage) {
        console.log('[clearImageDisplay] 画像非表示処理: src=', sourceImage.src);
    }
    if (imageContainer) {
        const style = window.getComputedStyle(sourceImage);
        console.log('[clearImageDisplay] img display:', style.display, 'visibility:', style.visibility, 'opacity:', style.opacity);
        const parentStyle = window.getComputedStyle(imageContainer);
        console.log('[clearImageDisplay] container display:', parentStyle.display, 'visibility:', parentStyle.visibility, 'opacity:', parentStyle.opacity);
    }
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
    imageContainer.classList.add('no-image');
    imageContainer.classList.remove('cropper-active');
    
    if (currentImageInfo) {
        currentImageInfo.style.display = 'none';
    }
    
    if (imageNavigation) {
        imageNavigation.style.display = 'none';
    }
}

// 現在の画像情報を更新
function updateCurrentImageInfo() {
    const currentImageInfo = document.getElementById('current-image-info');
    const currentImageName = document.getElementById('current-image-name');
    
    if (currentImageInfo && currentImageName && imageList.length > 0) {
        currentImageName.textContent = imageList[imageIndex];
        currentImageInfo.style.display = 'block';
    }
}

// 画像ナビゲーション更新
function updateImageNavigation() {
    const imageNavigation = document.getElementById('image-navigation');
    const imageCounter = document.getElementById('image-counter');
    const prevBtn = document.getElementById('prev-image-btn');
    const nextBtn = document.getElementById('next-image-btn');
    
    if (imageList.length > 0) {
        if (imageNavigation) imageNavigation.style.display = 'flex';
        if (imageCounter) imageCounter.textContent = `${imageIndex + 1} / ${imageList.length}`;
        if (prevBtn) prevBtn.disabled = imageIndex <= 0;
        if (nextBtn) nextBtn.disabled = imageIndex >= imageList.length - 1;
    } else {
        if (imageNavigation) imageNavigation.style.display = 'none';
    }
}

function updateCropInfo(data) {
    if (cropInfo) {
        cropInfo.innerHTML = `
            選択範囲の左上位置: X=${Math.round(data.x)}, Y=${Math.round(data.y)} | 
            現在のサイズ: ${Math.round(data.width)}×${Math.round(data.height)}px | 
            最終出力: 640×640px
        `;
    }
}

// 座標蓄積
function addCropCoordinate() {
    if (!cropper) {
        alert('画像が読み込まれていません');
        return;
    }
    
    const data = cropper.getData();
    const coord = {
        x: Math.round(data.x),
        y: Math.round(data.y),
        width: Math.round(data.width),
        height: Math.round(data.height),
        image: imageList[imageIndex] || 'unknown',
        timestamp: new Date().toLocaleTimeString()
    };
    
    cropCoords.push(coord);
    updateCoordinatesList();
    updateBoundingBox();
    
    console.log('座標追加:', coord);
}

function updateCoordinatesList() {
    const coordinatesList = document.getElementById('coordinates-list');
    const coordinatesCount = document.getElementById('coordinates-count');
    const clearAllBtn = document.getElementById('clear-all-btn');
    
    if (coordinatesCount) {
        coordinatesCount.textContent = `蓄積数: ${cropCoords.length}個`;
    }
    
    if (clearAllBtn) {
        clearAllBtn.disabled = cropCoords.length === 0;
    }
    
    if (!coordinatesList) return;
    
    if (cropCoords.length === 0) {
        coordinatesList.innerHTML = `
            <div class="text-center text-muted">
                <i class="bi bi-info-circle"></i> まだ座標が蓄積されていません
            </div>
        `;
        return;
    }
    
    coordinatesList.innerHTML = cropCoords.map((coord, index) => `
        <div class="card mb-2 border-light">
            <div class="card-body py-2">
                <div class="row align-items-center">
                    <div class="col-1">
                        <span class="badge bg-primary">${index + 1}</span>
                    </div>
                    <div class="col-7">
                        <small class="text-muted">画像:</small> <strong>${coord.image}</strong><br>
                        <small class="text-muted">座標:</small> X=${coord.x}, Y=${coord.y}, W=${coord.width}, H=${coord.height}
                    </div>
                    <div class="col-2">
                        <small class="text-muted">${coord.timestamp}</small>
                    </div>
                    <div class="col-2 text-end">
                        <button class="btn btn-outline-danger btn-sm" onclick="removeCoordinate(${index})" title="削除">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function removeCoordinate(index) {
    if (index >= 0 && index < cropCoords.length) {
        cropCoords.splice(index, 1);
        updateCoordinatesList();
        updateBoundingBox();
    }
}

function clearAllCoordinates() {
    if (cropCoords.length > 0 && confirm('全ての座標データをクリアしますか？')) {
        cropCoords = [];
        updateCoordinatesList();
        updateBoundingBox();
        clearBoundingBoxPreview();
    }
}

// 包括座標計算と表示
function getBoundingBox() {
    if (cropCoords.length === 0) return null;
    
    let minX = Math.min(...cropCoords.map(c => c.x));
    let minY = Math.min(...cropCoords.map(c => c.y));
    let maxX = Math.max(...cropCoords.map(c => c.x + c.width));
    let maxY = Math.max(...cropCoords.map(c => c.y + c.height));
    
    return {
        x: minX,
        y: minY,
        width: maxX - minX,
        height: maxY - minY
    };
}

function updateBoundingBox() {
    const boundingBoxSection = document.getElementById('bounding-box-section');
    const boundingBoxInfo = document.getElementById('bounding-box-info');
    const previewBtn = document.getElementById('preview-bbox-btn');
    const saveYamlBtn = document.getElementById('save-yaml-btn');
    const downloadAllBtn = document.getElementById('download-all-btn');
    
    if (cropCoords.length === 0) {
        if (boundingBoxSection) boundingBoxSection.style.display = 'none';
        return;
    }
    
    const bbox = getBoundingBox();
    if (!bbox) return;
    
    if (boundingBoxSection) boundingBoxSection.style.display = 'block';
    
    if (boundingBoxInfo) {
        boundingBoxInfo.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <strong>包括座標:</strong><br>
                    X: ${bbox.x}px, Y: ${bbox.y}px<br>
                    幅: ${bbox.width}px, 高さ: ${bbox.height}px
                </div>
                <div class="col-md-6">
                    <strong>統計情報:</strong><br>
                    蓄積座標数: ${cropCoords.length}個<br>
                    カバー範囲: ${bbox.width} × ${bbox.height}px
                </div>
            </div>
        `;
    }
    
    // ボタンの有効化
    if (previewBtn) previewBtn.disabled = false;
    if (saveYamlBtn) saveYamlBtn.disabled = false;
    if (downloadAllBtn) downloadAllBtn.disabled = imageList.length === 0;
}

function previewBoundingBox() {
    const bbox = getBoundingBox();
    if (!cropper || !bbox) return;
    
    // Cropperに包括座標を設定
    cropper.setData({
        x: bbox.x,
        y: bbox.y,
        width: bbox.width,
        height: bbox.height
    });
    
    // プレビュー状態を表示
    const previewSection = document.getElementById('bounding-box-preview');
    const previewInfo = document.getElementById('preview-info');
    const clearPreviewBtn = document.getElementById('clear-preview-btn');
    
    if (previewSection) {
        previewSection.style.display = 'block';
        
        if (previewInfo) {
            previewInfo.innerHTML = `
                包括座標: X=${bbox.x}, Y=${bbox.y}, 幅=${bbox.width}, 高さ=${bbox.height}<br>
                <small>この範囲で全画像が切り抜かれます</small>
            `;
        }
    }
    
    if (clearPreviewBtn) {
        clearPreviewBtn.style.display = 'inline-block';
    }
    
    // Cropperコンテナにプレビュー用のクラスを追加
    const cropperContainer = document.querySelector('.cropper-container');
    if (cropperContainer) {
        cropperContainer.classList.add('preview-mode');
    }
}

function clearBoundingBoxPreview() {
    const previewSection = document.getElementById('bounding-box-preview');
    const clearPreviewBtn = document.getElementById('clear-preview-btn');
    
    if (previewSection) {
        previewSection.style.display = 'none';
    }
    
    if (clearPreviewBtn) {
        clearPreviewBtn.style.display = 'none';
    }
    
    // Cropperコンテナからプレビュー用のクラスを削除
    const cropperContainer = document.querySelector('.cropper-container');
    if (cropperContainer) {
        cropperContainer.classList.remove('preview-mode');
    }
    
    // Cropperを中央にリセット
    if (cropper) {
        resetCrop();
    }
}

// Cropper操作関数
function resetCrop() {
    if (cropper) {
        cropper.reset();
    }
}

function cropToCenter() {
    if (!cropper) return;
    
    const imageData = cropper.getImageData();
    const centerX = imageData.naturalWidth / 2;
    const centerY = imageData.naturalHeight / 2;
    const size = Math.min(imageData.naturalWidth, imageData.naturalHeight) * 0.6;
    
    cropper.setData({
        x: centerX - size / 2,
        y: centerY - size / 2,
        width: size,
        height: size
    });
}

function adjustCropSize(delta) {
    if (!cropper) return;
    
    const data = cropper.getData();
    const newSize = Math.max(50, data.width + delta); // 最小サイズ50px
    
    // 中心を維持してサイズ変更
    const centerX = data.x + data.width / 2;
    const centerY = data.y + data.height / 2;
    
    cropper.setData({
        x: centerX - newSize / 2,
        y: centerY - newSize / 2,
        width: newSize,
        height: newSize
    });
}

// YAMLファイル保存
function saveBoundingBoxToYaml() {
    const bbox = getBoundingBox();
    if (!bbox) {
        alert('包括座標がありません');
        return;
    }
    
    const yamlData = {
        bounding_box: bbox,
        coordinates: cropCoords,
        project: currentProject ? currentProject.name : 'unknown',
        folder: currentFolder || 'unknown',
        created_at: new Date().toISOString(),
        total_coordinates: cropCoords.length
    };
    
    // YAMLとして保存するAPI呼び出し
    fetch('/crop_app/save-bounding-box-yaml/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify(yamlData)
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert(`YAMLファイルを保存しました: ${data.filename}`);
        } else {
            alert(`保存エラー: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('YAML保存エラー:', error);
        alert('YAML保存中にエラーが発生しました');
    });
}


// 全画像一括切り抜き＆croppedフォルダ保存
function cropAndSaveAllImagesToCroppedFolder() {
    if (!currentFolder || !currentProject) {
        alert('プロジェクトとフォルダを選択してください。');
        return;
    }
    if (!cropCoords || cropCoords.length === 0) {
        alert('切り抜き座標がありません。まず座標を蓄積してください。');
        return;
    }
    // 包括座標を取得
    const bbox = getBoundingBox();
    if (!bbox) {
        alert('包括座標が計算できません。');
        return;
    }
    if (!confirm('このフォルダ内の全画像を包括座標で切り抜き、croppedフォルダに保存します。よろしいですか？')) {
        return;
    }

    // サーバーにリクエストを送信
    fetch('/crop_app/api/crop-and-save-all/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            project_id: currentProject.id,
            folder_path: currentFolder,
            bounding_box: bbox
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('全画像の切り抜き＆保存が完了しました。\ncroppedフォルダを確認してください。');
        } else {
            alert('エラー: ' + (data.message || '一括切り抜きに失敗しました。'));
        }
    })
    .catch(error => {
        alert('通信エラー: ' + error);
    });
}


// ナビゲーション関数
function loadPreviousImage() {
    if (imageIndex > 0) {
        imageIndex--;
        showImage();
        updateImageNavigation();
    }
}

function loadNextImage() {
    if (imageIndex < imageList.length - 1) {
        imageIndex++;
        showImage();
        updateImageNavigation();
    }
}

// パス取得関数
function getCurrentPath() {
    const selectionMode = document.getElementById('selection-mode')?.value;
    
    switch(selectionMode) {
        case 'predefined':
            const folderPath = document.getElementById('folder-path')?.value;
            return folderPath || '';
        case 'project':
            return currentFolder || '';
        case 'custom':
            const customPath = document.getElementById('custom-path')?.value;
            return customPath || '';
        default:
            return '';
    }
}

// ショートカットキー
window.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        loadPreviousImage();
    }
    if (e.ctrlKey && e.key === 'ArrowRight') {
        e.preventDefault();
        loadNextImage();
    }
    if (e.key === ' ') {
        e.preventDefault();
        addCropCoordinate();
    }
    if (e.key === 'p' || e.key === 'P') {
        e.preventDefault();
        previewBoundingBox();
    }
    if (e.key === 'Escape') {
        e.preventDefault();
        clearBoundingBoxPreview();
    }
});

// 初期化
window.addEventListener('DOMContentLoaded', function() {
    console.log('画像切り抜きアプリ初期化開始');
    
    // プロジェクト一覧を読み込み
    loadProjects();
    
    // 選択モードの初期設定
    updateSelectionMode();
    
    console.log('初期化完了');
});


// Cropper.js 準備完了イベント
document.addEventListener('cropperReady', function(event) {
    console.log('Cropper.js準備完了:', event.detail);
});


function tryNextAlternative(alternatives, index) {
    if (index >= alternatives.length) {
        // すべての代替パスが失敗
        showImageError(`画像読み込み失敗: ${imageList[imageIndex]}<br>すべての代替パスでアクセスできませんでした`);
        return;
    }
    
    const testImg = new Image();
    const currentPath = alternatives[index];
    
    console.log(`代替パス ${index + 1}/${alternatives.length} を試行:`, currentPath);
    
    testImg.onload = () => {
        console.log('代替パス成功:', currentPath);
        sourceImage.src = currentPath;
        initializeCropper();
        updateCurrentImageInfo();
    };
    
    testImg.onerror = () => {
        console.log('代替パス失敗:', currentPath);
        // 次の代替パスを試行
        setTimeout(() => tryNextAlternative(alternatives, index + 1), 100);
    };
    
    testImg.src = currentPath;
}

// プロジェクト画像パス検証
function validateProjectImagePath() {
    if (!currentProject || !currentFolder || !imageList.length) {
        console.warn('画像パス検証: 必要な情報が不足しています', {
            currentProject: !!currentProject,
            currentFolder: !!currentFolder,
            imageListLength: imageList.length
        });
        return false;
    }
    
    console.log('画像パス検証:', {
        projectName: currentProject.name,
        projectId: currentProject.id,
        folderPath: currentFolder,
        folderName: currentFolder.split(/[/\\]/).pop(),
        currentImage: imageList[imageIndex],
        imageIndex: imageIndex,
        totalImages: imageList.length
    });
    
    return true;
}

// デバッグ情報を詳細表示
function showDetailedDebugInfo() {
    console.group('詳細デバッグ情報');
    console.log('現在の状態:', {
        selectionMode: document.getElementById('selection-mode')?.value,
        currentProject: currentProject,
        currentFolder: currentFolder,
        imageList: imageList,
        imageIndex: imageIndex,
        allProjects: allProjects
    });
    
    if (currentProject) {
        console.log('プロジェクト詳細:', {
            id: currentProject.id,
            name: currentProject.name,
            folders: currentProject.folders,
            created_at: currentProject.created_at
        });
    }
    
    console.groupEnd();
}

// crop.html内の「シンプルな画像初期化スクリプト」やupdateImageDisplay等でno-imageクラスを付与する処理は削除してください。
// 画像表示・Cropper初期化の制御はcrop.js(showImage, initializeCropper)に一元化します。
// 他のスクリプトでno-imageクラスを付与すると競合が発生するため、showImage, showImageError, showImageWarning, clearImageDisplay などでのみno-imageクラスを制御するようにしてください。
