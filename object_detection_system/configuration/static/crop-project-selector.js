// crop-project-selector.js - プロジェクト名からフォルダ選択機能

// プロジェクトフォルダのデータ
let projectFoldersData = {};

// 選択モードの変更処理
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
            // プロジェクトフォルダデータを読み込み
            loadProjectFolders();
            break;
        case 'custom':
            customSelection.style.display = 'block';
            break;
    }
    
    // 選択された画像情報をクリア
    clearSelectedImageInfo();
}

// プロジェクトフォルダデータの読み込み
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
            console.error('プロジェクトフォルダの取得に失敗:', data.error);
            alert('プロジェクトフォルダの取得に失敗しました: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error loading project folders:', error);
        alert('プロジェクトフォルダの取得中にエラーが発生しました');
    });
}

// プロジェクト選択リストを作成
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

// プロジェクト選択時のフォルダ更新
function updateProjectFolders() {
    const projectName = document.getElementById('project-name').value;
    const projectFolderContainer = document.getElementById('project-folder-container');
    const projectFolderSelect = document.getElementById('project-folder');
    
    if (!projectName || !projectFoldersData[projectName]) {
        projectFolderContainer.style.display = 'none';
        return;
    }
    
    // フォルダ選択リストを更新
    projectFolderSelect.innerHTML = '<option value="">フォルダを選択してください...</option>';
    
    const projectInfo = projectFoldersData[projectName];
    projectInfo.subfolders.forEach(folder => {
        const option = document.createElement('option');
        option.value = folder.path;
        option.textContent = `${folder.name} (${folder.image_count}枚)`;
        projectFolderSelect.appendChild(option);
    });
    
    projectFolderContainer.style.display = 'block';
    
    // 選択された画像情報をクリア
    clearSelectedImageInfo();
}

// プロジェクトパスの更新
function updateProjectPath() {
    const projectFolder = document.getElementById('project-folder').value;
    
    if (projectFolder) {
        // 選択されたフォルダパスを設定
        selectedFolderPath = projectFolder;
        
        // 選択された画像情報をクリア
        clearSelectedImageInfo();
        
        // ナビゲーションを非表示
        const navigation = document.getElementById('image-navigation');
        if (navigation) {
            navigation.style.display = 'none';
        }
        currentImageList = [];
        currentImageIndex = 0;
    }
}

// 現在の選択されたフォルダパスを取得
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

// 選択された画像情報をクリア
function clearSelectedImageInfo() {
    const selectedImageInfo = document.getElementById('selected-image-info');
    if (selectedImageInfo) {
        selectedImageInfo.style.display = 'none';
    }
    selectedImagePath = null;
    
    // 画像表示をクリア
    const sourceImage = document.getElementById('source-image');
    if (sourceImage) {
        sourceImage.src = '';
    }
    
    // Cropperを初期化
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
}

// 元のupdateImagePath関数を更新
function updateImagePath() {
    const selectedValue = document.getElementById('folder-path').value;
    const customPathInput = document.getElementById('custom-path');
    
    if (selectedValue === 'custom') {
        if (customPathInput) {
            customPathInput.style.display = 'inline-block';
            customPathInput.focus();
        }
    } else {
        if (customPathInput) {
            customPathInput.style.display = 'none';
        }
        clearSelectedImageInfo();
    }
}
