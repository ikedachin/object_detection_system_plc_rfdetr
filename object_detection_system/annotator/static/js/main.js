// メインページのJavaScript
document.addEventListener('DOMContentLoaded', function() {
    // ラベルバッジの動的カラー設定
    const labelBadges = document.querySelectorAll('.label-badge');
    labelBadges.forEach(badge => {
        const color = badge.getAttribute('data-color');
        if (color) {
            badge.style.backgroundColor = color;
        }
    });

    const splitDatasetBtn = document.getElementById('split-dataset-btn');
    const loadProjectImagesBtn = document.getElementById('load-project-images-btn');
    const loadProjectImagesBtnEmpty = document.getElementById('load-project-images-btn-empty');
    
    // プロジェクト画像読み込みボタンの処理（共通関数）
    function handleLoadProjectImages(btn) {
        const projectId = btn.dataset.projectId;
        
        if (!projectId) {
            alert('プロジェクトIDが取得できませんでした。');
            return;
        }
        
        const originalContent = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> 読み込み中...';
        
        fetch(`/annotator/api/load_project_images/${projectId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert('エラー: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('エラーが発生しました');
        })
        .finally(() => {
            btn.disabled = false;
            btn.innerHTML = originalContent;
        });
    }
    
    // プロジェクト画像読み込みボタンの処理
    if (loadProjectImagesBtn) {
        loadProjectImagesBtn.addEventListener('click', function() {
            handleLoadProjectImages(this);
        });
    }
    
    if (loadProjectImagesBtnEmpty) {
        loadProjectImagesBtnEmpty.addEventListener('click', function() {
            handleLoadProjectImages(this);
        });
    }
    
    // プロジェクトが選択されていない場合は機能を無効にする
    if (!splitDatasetBtn && !loadProjectImagesBtn && !loadProjectImagesBtnEmpty) {
        console.log('プロジェクトが選択されていないため、一部機能が無効になっています。');
        return;
    }
    
    let splitModal, confirmSplitBtn;
    
    // データセット分割ボタンの処理
    if (splitDatasetBtn) {
        splitModal = new bootstrap.Modal(document.getElementById('splitModal'));
        confirmSplitBtn = document.getElementById('confirm-split');

        // データセット分割ボタン
        splitDatasetBtn.addEventListener('click', function() {
            splitModal.show();
        });

        // 分割実行ボタン
        confirmSplitBtn.addEventListener('click', function() {
        const splitRatio = document.getElementById('split-ratio').value;
        const imageSize = document.getElementById('image-size').value;
        
        this.disabled = true;
        this.textContent = '分割中...';
        
        fetch('/annotator/api/split_dataset/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                split_ratio: parseFloat(splitRatio),
                image_size: parseInt(imageSize),
                projectname: infoToSplitDataset.projectname,
                cropped: infoToSplitDataset.cropped,
                current_project: infoToSplitDataset.currentProject,
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert(data.message);
                splitModal.hide();
            } else {
                alert('エラー: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('エラーが発生しました');
        })
        .finally(() => {
            this.disabled = false;
            this.textContent = '分割実行';
        });
        });
    }
    
    // 表示切り替え機能
    initViewToggle();
    
    // ラベル管理機能を初期化
    initLabelManagement();
});

// ラベル管理機能の初期化
function initLabelManagement() {
    let editingLabelId = null;
    const labelModal = new bootstrap.Modal(document.getElementById('labelModal'));
    
    // ラベル追加ボタン
    document.getElementById('add-label-btn').addEventListener('click', function() {
        editingLabelId = null;
        document.getElementById('labelModalLabel').textContent = 'ラベルを追加';
        document.getElementById('labelName').value = '';
        document.getElementById('labelColor').value = '#FF0000';
        labelModal.show();
    });
    
    // ラベル編集・削除ボタン（イベント委譲）
    document.getElementById('labels-list').addEventListener('click', function(e) {
        // 編集ボタンがクリックされた場合
        if (e.target.closest('.edit-label-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.edit-label-btn');
            editingLabelId = btn.getAttribute('data-label-id');
            
            const labelName = btn.getAttribute('data-label-name') || '';
            const labelColor = btn.getAttribute('data-label-color') || '#FF0000';
            
            document.getElementById('labelModalLabel').textContent = 'ラベルを編集';
            document.getElementById('labelName').value = labelName;
            document.getElementById('labelColor').value = labelColor;
            labelModal.show();
            return;
        }
        
        // 削除ボタンがクリックされた場合
        if (e.target.closest('.delete-label-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.delete-label-btn');
            const labelName = btn.getAttribute('data-label-name') || '';
            const labelId = btn.getAttribute('data-label-id');
            
            if (confirm(`ラベル「${labelName}」を削除しますか？\n※このラベルが使用されているアノテーションがある場合は削除できません。`)) {
                deleteLabel(labelId);
            }
            return;
        }
    });
    
    // ラベル保存ボタン
    document.getElementById('saveLabelBtn').addEventListener('click', function() {
        const name = document.getElementById('labelName').value.trim();
        const color = document.getElementById('labelColor').value;
        
        if (!name) {
            alert('ラベル名を入力してください');
            return;
        }
        
        if (editingLabelId) {
            updateLabel(editingLabelId, name, color);
        } else {
            addLabel(name, color);
        }
    });
}

// ラベル追加
function addLabel(name, color) {
    fetch('/annotator/api/add_label/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ name, color })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // ラベル一覧を更新
            addLabelToUI(data.label);
            // モーダルを閉じる
            bootstrap.Modal.getInstance(document.getElementById('labelModal')).hide();
        } else {
            alert('エラー: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('エラーが発生しました');
    });
}

// ラベル更新
function updateLabel(labelId, name, color) {
    fetch(`/annotator/api/update_label/${labelId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ name, color })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // ラベル一覧を更新
            updateLabelInUI(data.label);
            // モーダルを閉じる
            bootstrap.Modal.getInstance(document.getElementById('labelModal')).hide();
            alert('ラベルを更新しました');
        } else {
            alert('エラー: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('エラーが発生しました');
    });
}

// ラベル削除
function deleteLabel(labelId) {
    fetch(`/annotator/api/delete_label/${labelId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // ラベル一覧から削除
            removeLabelFromUI(labelId);
            alert(data.message);
        } else {
            alert('エラー: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('エラーが発生しました');
    });
}

// UIにラベルを追加
function addLabelToUI(label) {
    const labelsList = document.getElementById('labels-list');
    
    // "ラベルがありません"メッセージを削除
    const noLabelsMessage = document.getElementById('no-labels-message');
    if (noLabelsMessage) {
        noLabelsMessage.remove();
    }
    
    const labelItem = document.createElement('div');
    labelItem.className = 'label-item d-flex align-items-center mb-2 p-2 border rounded';
    labelItem.setAttribute('data-label-id', label.id);
    labelItem.innerHTML = `
        <span class="color-indicator rounded-circle me-2" 
              style="width: 16px; height: 16px; background-color: ${label.color}; border: 1px solid rgba(0,0,0,0.1);"></span>
        <span class="flex-grow-1">${label.name}</span>
        <span class="text-muted me-2" style="font-size: 0.85em; opacity: 0.7;">
            (0)
        </span>
        <div class="btn-group">
            <button class="btn btn-outline-secondary btn-sm edit-label-btn" 
                    data-label-id="${label.id}"
                    data-label-name="${label.name}"
                    data-label-color="${label.color}"
                    title="編集">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-outline-danger btn-sm delete-label-btn" 
                    data-label-id="${label.id}"
                    data-label-name="${label.name}"
                    title="削除">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `;
    labelsList.appendChild(labelItem);
}

// UIのラベルを更新
function updateLabelInUI(label) {
    const labelItem = document.querySelector(`[data-label-id="${label.id}"]`);
    if (labelItem) {
        const colorIndicator = labelItem.querySelector('.color-indicator');
        const labelName = labelItem.querySelector('.flex-grow-1');
        const editBtn = labelItem.querySelector('.edit-label-btn');
        const deleteBtn = labelItem.querySelector('.delete-label-btn');
        
        // 色とラベル名を更新
        if (colorIndicator) colorIndicator.style.backgroundColor = label.color;
        if (labelName) labelName.textContent = label.name;
        
        // データ属性を更新
        if (editBtn) {
            editBtn.setAttribute('data-label-name', label.name);
            editBtn.setAttribute('data-label-color', label.color);
        }
        if (deleteBtn) {
            deleteBtn.setAttribute('data-label-name', label.name);
        }
        
        // 使用回数は変わらないのでそのまま
    }
}

// UIからラベルを削除
function removeLabelFromUI(labelId) {
    const labelItem = document.querySelector(`[data-label-id="${labelId}"]`);
    if (labelItem) {
        labelItem.remove();
        
        // ラベルが全て削除された場合、メッセージを表示
        const labelsList = document.getElementById('labels-list');
        if (labelsList.children.length === 0) {
            const noLabelsMessage = document.createElement('p');
            noLabelsMessage.className = 'text-muted';
            noLabelsMessage.id = 'no-labels-message';
            noLabelsMessage.textContent = 'ラベルがありません。「ラベル追加」ボタンをクリックして追加してください。';
            labelsList.appendChild(noLabelsMessage);
        }
    }
}

// 表示切り替え機能の初期化
function initViewToggle() {
    const gridViewBtn = document.getElementById('grid-view-btn');
    const listViewBtn = document.getElementById('list-view-btn');
    const imagesGrid = document.getElementById('images-grid');
    const imagesList = document.getElementById('images-list');
    
    // 初期状態：グリッド表示をアクティブに
    let currentView = localStorage.getItem('imageViewMode') || 'grid';
    
    // 初期表示設定
    if (currentView === 'list') {
        showListView();
    } else {
        showGridView();
    }
    
    // グリッド表示ボタンのクリックイベント
    gridViewBtn.addEventListener('click', function() {
        showGridView();
        localStorage.setItem('imageViewMode', 'grid');
    });
    
    // リスト表示ボタンのクリックイベント
    listViewBtn.addEventListener('click', function() {
        showListView();
        localStorage.setItem('imageViewMode', 'list');
    });
    
    function showGridView() {
        // ボタンの状態を更新
        gridViewBtn.classList.add('active');
        listViewBtn.classList.remove('active');
        
        // 表示を切り替え
        imagesGrid.classList.remove('d-none');
        imagesList.classList.add('d-none');
        
        currentView = 'grid';
    }
    
    function showListView() {
        // ボタンの状態を更新
        listViewBtn.classList.add('active');
        gridViewBtn.classList.remove('active');
        
        // 表示を切り替え
        imagesGrid.classList.add('d-none');
        imagesList.classList.remove('d-none');
        
        currentView = 'list';
    }
}

// CSRFトークンを取得する関数
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
