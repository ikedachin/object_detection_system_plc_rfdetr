// アノテーション機能のJavaScript
class AnnotationCanvas {
    constructor(canvasId) {
        console.log('AnnotationCanvas constructor called with:', canvasId);
        this.canvas = document.getElementById(canvasId);
        
        if (!this.canvas) {
            console.error('Canvas element not found:', canvasId);
            alert('Canvas要素が見つかりません: ' + canvasId);
            return;
        }
        
        console.log('Canvas element found:', this.canvas);
        this.ctx = this.canvas.getContext('2d');
        console.log('Canvas context:', this.ctx);
        
        this.image = new Image();
        this.annotations = [];
        this.currentAnnotation = null;
        this.selectedLabelId = null;
        this.selectedLabelName = null;
        this.selectedLabelColor = '#FF0000';
        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.hoveredAnnotationId = null; // ホバー中のアノテーションID
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
        this.canvas.addEventListener('click', this.onCanvasClick.bind(this));
    }
    
    loadImage(imageUrl) {
        console.log('画像を読み込み中:', imageUrl);
        
        // 画像読み込み前にCanvasを初期化
        this.canvas.width = 800;
        this.canvas.height = 600;
        this.ctx.fillStyle = '#f8f9fa';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // ローディング表示
        this.ctx.fillStyle = '#6c757d';
        this.ctx.font = '18px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('画像を読み込み中...', this.canvas.width / 2, this.canvas.height / 2);
        this.ctx.textAlign = 'left';
        
        this.image.onload = () => {
            console.log('画像読み込み成功');
            console.log('画像の自然サイズ:', this.image.naturalWidth, 'x', this.image.naturalHeight);
            this.canvas.width = this.image.naturalWidth;
            this.canvas.height = this.image.naturalHeight;
            console.log('キャンバスサイズ:', this.canvas.width, 'x', this.canvas.height);
            this.resizeCanvas();
            this.redraw();
        };
        
        this.image.onerror = (e) => {
            console.error('画像読み込み失敗:', e);
            console.error('URL:', imageUrl);
            
            // エラー表示
            this.ctx.fillStyle = '#f8d7da';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#721c24';
            this.ctx.font = '16px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('画像の読み込みに失敗しました', this.canvas.width / 2, this.canvas.height / 2 - 20);
            this.ctx.fillText('URL: ' + imageUrl, this.canvas.width / 2, this.canvas.height / 2 + 10);
            this.ctx.textAlign = 'left';
            
            // アラートも表示
            setTimeout(() => {
                alert('画像の読み込みに失敗しました。URLを確認してください: ' + imageUrl);
            }, 100);
        };
        
        // 画像読み込み開始
        this.image.crossOrigin = 'anonymous';
        const cacheBuster = '?t=' + Date.now();
        this.image.src = imageUrl + cacheBuster;
        
        console.log('画像読み込み開始:', this.image.src);
    }
    
    resizeCanvas() {
        console.log('resizeCanvas called');
        
        if (!this.image || !this.image.naturalWidth || !this.image.naturalHeight) {
            console.error('Invalid image for resizing');
            return;
        }
        
        console.log('Image natural dimensions:', this.image.naturalWidth, 'x', this.image.naturalHeight);
        
        // コンテナサイズを取得
        const container = this.canvas.parentElement;
        const containerWidth = container.clientWidth - 40; // パディングを考慮
        // const maxHeight = Math.min(window.innerHeight * 0.7, 600); // 最大高さを制限
        const maxHeight = window.innerHeight * 0.8; // 最大高さを制限
        
        console.log('Container constraints:', containerWidth, 'x', maxHeight);
        
        // 画像のアスペクト比を維持してキャンバスサイズを計算
        const imageAspectRatio = this.image.naturalWidth / this.image.naturalHeight;
        const containerAspectRatio = containerWidth / maxHeight;
        
        if (imageAspectRatio > containerAspectRatio) {
            // 幅が制限要因
            this.canvas.width = containerWidth;
            this.canvas.height = containerWidth / imageAspectRatio;
        } else {
            // 高さが制限要因
            this.canvas.height = maxHeight;
            this.canvas.width = maxHeight * imageAspectRatio;
        }
        
        // スケール係数を計算
        this.scale = this.canvas.width / this.image.naturalWidth;
        
        console.log('Canvas resized to:', this.canvas.width, 'x', this.canvas.height);
        console.log('Scale factor:', this.scale);
        
        // CSSでキャンバスサイズを明示的に設定
        this.canvas.style.width = this.canvas.width + 'px';
        this.canvas.style.height = this.canvas.height + 'px';
    }
    
    onMouseDown(e) {
        if (!this.selectedLabelId) {
            alert('ラベルを選択してください');
            return;
        }
        
        const rect = this.canvas.getBoundingClientRect();
        this.startX = e.clientX - rect.left;
        this.startY = e.clientY - rect.top;
        this.isDrawing = true;
    }
    
    onMouseMove(e) {
        if (!this.isDrawing) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        
        this.redraw();
        this.drawCurrentBox(this.startX, this.startY, currentX, currentY);
    }
    
    onMouseUp(e) {
        if (!this.isDrawing) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;
        
        const minX = Math.min(this.startX, endX);
        const minY = Math.min(this.startY, endY);
        const maxX = Math.max(this.startX, endX);
        const maxY = Math.max(this.startY, endY);
        
        const width = maxX - minX;
        const height = maxY - minY;
        
        if (width > 10 && height > 10) {
            // Canvas座標を画像座標に変換して正規化BBox形式に変換
            const imageX = minX / this.scale;
            const imageY = minY / this.scale;
            const imageWidth = width / this.scale;
            const imageHeight = height / this.scale;
            
            // 正規化BBox形式（正規化された中心座標と幅・高さ）
            const x_center = (imageX + imageWidth / 2) / this.image.naturalWidth;
            const y_center = (imageY + imageHeight / 2) / this.image.naturalHeight;
            const norm_width = imageWidth / this.image.naturalWidth;
            const norm_height = imageHeight / this.image.naturalHeight;
            
            const annotation = {
                id: Date.now(), // 一時的なID
                label_id: this.selectedLabelId,
                label_name: this.selectedLabelName,
                label_color: this.selectedLabelColor,
                x_center: x_center,
                y_center: y_center,
                width: norm_width,
                height: norm_height
            };
            
            this.annotations.push(annotation);
            this.updateAnnotationsList();
        }
        
        this.isDrawing = false;
        this.redraw();
    }
    
    onCanvasClick(e) {
        if (this.isDrawing) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;
        
        // クリックされた座標にあるアノテーションを検索
        for (let i = this.annotations.length - 1; i >= 0; i--) {
            const ann = this.annotations[i];
            const x = (ann.x_center - ann.width / 2) * this.image.naturalWidth * this.scale;
            const y = (ann.y_center - ann.height / 2) * this.image.naturalHeight * this.scale;
            const w = ann.width * this.image.naturalWidth * this.scale;
            const h = ann.height * this.image.naturalHeight * this.scale;
            
            if (clickX >= x && clickX <= x + w && clickY >= y && clickY <= y + h) {
                this.highlightAnnotation(ann.id);
                break;
            }
        }
    }
    
    drawCurrentBox(x1, y1, x2, y2) {
        this.ctx.strokeStyle = this.selectedLabelColor;
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 5]);
        this.ctx.strokeRect(
            Math.min(x1, x2),
            Math.min(y1, y2),
            Math.abs(x2 - x1),
            Math.abs(y2 - y1)
        );
        this.ctx.setLineDash([]);
    }
    
    redraw() {
        console.log('redraw called');
        
        // キャンバスをクリア
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 画像が準備完了しているかチェック
        if (this.image && this.image.complete && this.image.naturalWidth > 0) {
            console.log('Drawing image to canvas');
            this.ctx.drawImage(this.image, 0, 0, this.canvas.width, this.canvas.height);
        } else {
            console.warn('Image not ready for drawing');
            // 読み込み中の表示
            this.ctx.fillStyle = '#f8f9fa';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#6c757d';
            this.ctx.font = '16px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('画像を読み込み中...', this.canvas.width / 2, this.canvas.height / 2);
            this.ctx.textAlign = 'left';
            return; // 画像が読み込まれていない場合はアノテーションも描画しない
        }
        
        // 既存のアノテーションを描画
        this.annotations.forEach(ann => {
            // ホバー中のアノテーション以外を通常通り描画
            if (ann.id !== this.hoveredAnnotationId) {
                this.drawAnnotation(ann);
            }
        });
        
        // ホバー中のアノテーションを薄い色で描画
        if (this.hoveredAnnotationId !== null) {
            const hoveredAnnotation = this.annotations.find(ann => ann.id === this.hoveredAnnotationId);
            if (hoveredAnnotation) {
                this.drawAnnotation(hoveredAnnotation, true); // ホバー状態で描画
            }
        }
        
        console.log('redraw completed');
    }
    
    drawAnnotation(annotation, isHovered = false) {
        if (!this.image || !this.image.naturalWidth) {
            return; // 画像が読み込まれていない場合は描画しない
        }
        
        // 正規化BBox形式からキャンバス座標に変換
        const x = (annotation.x_center - annotation.width / 2) * this.image.naturalWidth * this.scale;
        const y = (annotation.y_center - annotation.height / 2) * this.image.naturalHeight * this.scale;
        const w = annotation.width * this.image.naturalWidth * this.scale;
        const h = annotation.height * this.image.naturalHeight * this.scale;
        
        // ホバー中の場合は内部を薄く塗りつぶし
        if (isHovered) {
            // バウンディングボックスの内部を薄い色で塗りつぶし
            this.ctx.globalAlpha = 0.2;
            this.ctx.fillStyle = annotation.label_color;
            this.ctx.fillRect(x, y, w, h);
            this.ctx.globalAlpha = 1.0;
        }
        
        // 矩形の枠を描画
        this.ctx.strokeStyle = annotation.label_color;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, w, h);
        
        // ラベル名を描画（背景付き）
        this.ctx.font = '14px Arial';
        const textMetrics = this.ctx.measureText(annotation.label_name);
        const textWidth = textMetrics.width;
        const textHeight = 14;
        
        // 背景を描画
        this.ctx.fillStyle = annotation.label_color;
        this.ctx.fillRect(x, y - textHeight - 4, textWidth + 8, textHeight + 4);
        
        // テキストを描画
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillText(annotation.label_name, x + 4, y - 4);
    }
    
    setSelectedLabel(labelId, labelName, labelColor) {
        this.selectedLabelId = labelId;
        this.selectedLabelName = labelName;
        this.selectedLabelColor = labelColor;
        
        document.getElementById('selected-label').textContent = labelName;
    }
    
    loadExistingAnnotations(annotations) {
        this.annotations = annotations;
        this.updateAnnotationsList();
        this.redraw();
    }
    
    updateAnnotationsList() {
        const listContainer = document.getElementById('annotations-list');
        listContainer.innerHTML = '';
        
        this.annotations.forEach((ann, index) => {
            const item = document.createElement('div');
            item.className = 'annotation-item';
            item.dataset.annotationId = ann.id;
            item.innerHTML = `
                <div class="annotation-label" style="border-color: ${ann.label_color};">
                    ${ann.label_name}
                </div>
                <div class="annotation-coords d-flex align-items-center justify-content-between">
                    <span>位置: (${(ann.x_center * 100).toFixed(1)}%, ${(ann.y_center * 100).toFixed(1)}%)</span>
                    <button class="btn btn-danger btn-lg fs-3 px-3 py-0 delete-annotation" style="line-height:1;" title="削除" onclick="annotationCanvas.deleteAnnotation(${ann.id})">×</button>
                </div>
            `;
            
            item.addEventListener('click', () => {
                this.highlightAnnotation(ann.id);
            });
            
            // ホバー時にバウンディングボックスをハイライト
            item.addEventListener('mouseenter', () => {
                this.hoverAnnotation(ann.id);
            });
            
            item.addEventListener('mouseleave', () => {
                this.clearHoverAnnotation();
            });
            
            listContainer.appendChild(item);
        });
    }
    
    highlightAnnotation(annotationId) {
        // リスト内のハイライトを更新
        document.querySelectorAll('.annotation-item').forEach(item => {
            item.classList.remove('highlighted');
        });
        
        const item = document.querySelector(`[data-annotation-id="${annotationId}"]`);
        if (item) {
            item.classList.add('highlighted');
        }
    }
    
    deleteAnnotation(annotationId) {
        this.annotations = this.annotations.filter(ann => ann.id !== annotationId);
        this.updateAnnotationsList();
        this.redraw();
    }
    
    clearAllAnnotations() {
        this.annotations = [];
        this.updateAnnotationsList();
        this.redraw();
    }
    
    getAnnotationsForSave() {
        return this.annotations.map(ann => ({
            label_id: ann.label_id,
            x_center: ann.x_center,
            y_center: ann.y_center,
            width: ann.width,
            height: ann.height
        }));
    }
    
    hoverAnnotation(annotationId) {
        this.hoveredAnnotationId = annotationId;
        this.redraw();
    }
    
    clearHoverAnnotation() {
        this.hoveredAnnotationId = null;
        this.redraw();
    }
}

// アプリケーション初期化
let annotationCanvas;

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM読み込み完了');
    
    // プロジェクトが選択されているかチェック
    if (typeof window.projectSelected !== 'undefined' && !window.projectSelected) {
        console.log('プロジェクトが選択されていません。データ読み込みをスキップします。');
        return;
    }
    
    // データの存在確認
    if (typeof window.imageData === 'undefined') {
        console.error('imageData is not defined');
        alert('画像データの読み込みに失敗しました。ページを再読み込みしてください。');
        return;
    }
    
    if (typeof window.labelsData === 'undefined') {
        console.error('labelsData is not defined');
        alert('ラベルデータの読み込みに失敗しました。ページを再読み込みしてください。');
        return;
    }
    
    if (typeof window.existingAnnotations === 'undefined') {
        console.error('existingAnnotations is not defined');
        window.existingAnnotations = [];
    }
    
    // グローバル変数として設定
    window.imageData = window.imageData;
    window.labelsData = window.labelsData;
    window.existingAnnotations = window.existingAnnotations;
    
    console.log('画像データ:', window.imageData);
    console.log('ラベルデータ:', window.labelsData);
    console.log('既存アノテーション:', window.existingAnnotations);
    
    // アノテーションキャンバスを初期化
    annotationCanvas = new AnnotationCanvas('annotation-canvas');
    
    if (!annotationCanvas.canvas) {
        console.error('Canvas initialization failed');
        alert('キャンバスの初期化に失敗しました。');
        return;
    }
    
    // 画像を読み込み
    console.log('画像読み込み開始:', window.imageData.url);
    annotationCanvas.loadImage(window.imageData.url);
    
    // 既存のアノテーションを読み込み
    annotationCanvas.loadExistingAnnotations(window.existingAnnotations);
    
    // 既存のラベルボタンに色を適用
    initializeLabelButtonColors();
    
    // ラベル管理機能を初期化
    initLabelManagement();
    
    // 初期化時にbackdropをクリーンアップ（既存の残骸を削除）
    cleanupModalBackdrops();
    
    // ラベルボタンのイベントリスナー（シンプルな選択のみ）
    document.getElementById('label-buttons').addEventListener('click', function(e) {
        if (e.target.closest('.label-btn')) {
            const btn = e.target.closest('.label-btn');
            // APIでis_activeを更新
            fetch('/annotator/api/set_active_label/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ label_id: btn.dataset.labelId })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    // UI上のアクティブ状態を更新
                    document.querySelectorAll('.label-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    annotationCanvas.setSelectedLabel(
                        parseInt(btn.dataset.labelId),
                        btn.dataset.labelName,
                        btn.dataset.labelColor
                    );
                    document.getElementById('selected-label').textContent = btn.dataset.labelName;
                } else {
                    alert('ラベル選択エラー: ' + data.message);
                }
            })
            .catch(err => {
                alert('ラベル選択通信エラー');
                console.error(err);
            });
        }
    });

    // 初期表示時にis_activeなラベルを自動選択
    window.addEventListener('DOMContentLoaded', function() {
        const labelButtons = document.querySelectorAll('.label-btn');
        let activeFound = false;
        labelButtons.forEach(btn => {
            if (btn.dataset.labelActive === 'true') {
                btn.classList.add('active');
                annotationCanvas.setSelectedLabel(
                    parseInt(btn.dataset.labelId),
                    btn.dataset.labelName,
                    btn.dataset.labelColor
                );
                document.getElementById('selected-label').textContent = btn.dataset.labelName;
                activeFound = true;
            }
        });
        // is_activeがなければ最初のラベルを選択
        if (!activeFound && labelButtons.length > 0) {
            const btn = labelButtons[0];
            btn.classList.add('active');
            annotationCanvas.setSelectedLabel(
                parseInt(btn.dataset.labelId),
                btn.dataset.labelName,
                btn.dataset.labelColor
            );
            document.getElementById('selected-label').textContent = btn.dataset.labelName;
        }
    });
    
    // 保存ボタン
    document.getElementById('save-btn').addEventListener('click', function() {
        const annotations = annotationCanvas.getAnnotationsForSave();
        console.log('Manual save triggered with annotations:', annotations);
        
        this.disabled = true;
        this.textContent = '保存中...';
        
        fetch(`/annotator/api/save_annotations/${window.imageData.id}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                annotations: annotations
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Manual save response:', data);
            if (data.status === 'success') {
                alert('保存しました');
            } else {
                alert('エラー: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Manual save error:', error);
            alert('エラーが発生しました');
        })
        .finally(() => {
            this.disabled = false;
            this.textContent = '保存';
        });
    });
    
    // 全削除ボタン
    document.getElementById('clear-all-btn').addEventListener('click', function() {
        if (confirm('全てのアノテーションを削除しますか？')) {
            annotationCanvas.clearAllAnnotations();
        }
    });
    
    
    // 自動保存機能付きナビゲーション
    function saveAndNavigate(url, buttonElement) {
        const annotations = annotationCanvas.getAnnotationsForSave();
        
        // ボタンを無効化してロード状態を表示
        let originalText = '';
        if (buttonElement) {
            buttonElement.disabled = true;
            originalText = buttonElement.innerHTML;
            buttonElement.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>保存中...';
        }
        
        // 常にアノテーションを保存してから移動（変更があってもなくても）
        console.log('Saving annotations before navigation...', annotations);
        
        fetch(`/annotator/api/save_annotations/${window.imageData.id}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                annotations: annotations
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Save response:', data);
            if (data.status === 'success') {
                console.log('アノテーションを自動保存しました');
                // 保存成功後にページ遷移
                window.location.href = url;
            } else {
                alert('保存エラー: ' + data.message);
                // エラー時はボタンを元に戻す
                if (buttonElement) {
                    buttonElement.disabled = false;
                    buttonElement.innerHTML = originalText;
                }
            }
        })
        .catch(error => {
            console.error('保存エラー:', error);
            if (confirm('保存に失敗しました。保存せずに移動しますか？')) {
                window.location.href = url;
            } else {
                // エラー時はボタンを元に戻す
                if (buttonElement) {
                    buttonElement.disabled = false;
                    buttonElement.innerHTML = originalText;
                }
            }
        });
    }
    
    // 前の画像ボタン
    const prevBtn = document.getElementById('prev-btn');
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            const prevUrl = this.dataset.prevUrl;
            if (prevUrl) {
                saveAndNavigate(prevUrl, this);
            }
        });
    }
    
    // 次の画像ボタン
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            const nextUrl = this.dataset.nextUrl;
            if (nextUrl) {
                saveAndNavigate(nextUrl, this);
            }
        });
    }
    
    // キーボードショートカット
    document.addEventListener('keydown', function(e) {
        // Ctrl+S で保存
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            document.getElementById('save-btn').click();
            return;
        }
        
        // 矢印キーでナビゲーション（テキスト入力中は無効）
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        if (e.key === 'ArrowLeft' && prevBtn) {
            e.preventDefault();
            const prevUrl = prevBtn.dataset.prevUrl;
            if (prevUrl) {
                saveAndNavigate(prevUrl, prevBtn);
            }
        } else if (e.key === 'ArrowRight' && nextBtn) {
            e.preventDefault();
            const nextUrl = nextBtn.dataset.nextUrl;
            if (nextUrl) {
                saveAndNavigate(nextUrl, nextBtn);
            }
        }
    });

    // ウィンドウリサイズ時の処理
    window.addEventListener('resize', function() {
        setTimeout(() => {
            annotationCanvas.resizeCanvas();
            annotationCanvas.redraw();
        }, 100);
    });
    
    // ラベル管理機能
    initLabelManagement();
});

// 既存のラベルボタンに色を適用する関数
function initializeLabelButtonColors() {
    const labelButtons = document.querySelectorAll('.label-btn');
    labelButtons.forEach(button => {
        const labelColor = button.dataset.labelColor;
        if (labelColor) {
            button.style.borderColor = labelColor;
        }
    });
}

// ラベル管理機能の初期化
function initLabelManagement() {
    let editingLabelId = null;
    const labelModal = new bootstrap.Modal(document.getElementById('labelModal'));
    const editLabelSelectModal = new bootstrap.Modal(document.getElementById('editLabelSelectModal'));
    
    // モーダルイベントハンドラーを追加してbackdropの問題を防ぐ
    const labelModalElement = document.getElementById('labelModal');
    const editLabelSelectModalElement = document.getElementById('editLabelSelectModal');
    
    // モーダルが表示された後にテキストフィールドにフォーカスを設定
    labelModalElement.addEventListener('shown.bs.modal', function () {
        const labelNameInput = document.getElementById('labelName');
        if (labelNameInput) {
            labelNameInput.focus();
            // 入力を有効にする
            labelNameInput.removeAttribute('disabled');
            labelNameInput.removeAttribute('readonly');
            labelNameInput.style.pointerEvents = 'auto';
        }
    });
    
    // モーダルが完全に隠れた後にbackdropをクリーンアップ
    labelModalElement.addEventListener('hidden.bs.modal', function () {
        document.body.classList.remove('modal-open');
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => backdrop.remove());
    });
    
    editLabelSelectModalElement.addEventListener('hidden.bs.modal', function () {
        document.body.classList.remove('modal-open');
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => backdrop.remove());
    });
    
    // ラベル追加ボタン
    document.getElementById('add-label-btn').addEventListener('click', function() {
        editingLabelId = null;
        document.getElementById('labelModalLabel').textContent = 'ラベルを追加';
        document.getElementById('labelName').value = '';
        document.getElementById('labelColor').value = '#FF0000';
        labelModal.show();
    });
    
    // ラベル編集ボタン
    document.getElementById('edit-label-btn').addEventListener('click', function() {
        showEditLabelSelectModal();
    });
    
    // ラベル編集選択モーダルを表示
    function showEditLabelSelectModal() {
        const editLabelList = document.getElementById('edit-label-list');
        editLabelList.innerHTML = '';
        
        // 現在のラベル一覧を取得
        const labelButtons = document.querySelectorAll('.label-btn');
        
        if (labelButtons.length === 0) {
            editLabelList.innerHTML = '<div class="alert alert-info">編集可能なラベルがありません。</div>';
        } else {
            labelButtons.forEach(btn => {
                const labelId = btn.dataset.labelId;
                const labelName = btn.dataset.labelName;
                const labelColor = btn.dataset.labelColor;
                
                // ラベルが使用されているかチェック
                const isUsed = annotationCanvas.annotations.some(annotation => 
                    annotation.label_id === parseInt(labelId)
                );
                
                const listItem = document.createElement('button');
                listItem.className = `list-group-item list-group-item-action d-flex justify-content-between align-items-center ${isUsed ? 'disabled' : ''}`;
                listItem.innerHTML = `
                    <div class="d-flex align-items-center">
                        <span class="color-indicator rounded-circle me-2" 
                              style="width: 16px; height: 16px; background-color: ${labelColor}; border: 1px solid rgba(0,0,0,0.1);"></span>
                        <span>${labelName}</span>
                    </div>
                    ${isUsed ? '<small class="text-muted">使用中</small>' : ''}
                `;
                
                if (!isUsed) {
                    listItem.addEventListener('click', function() {
                        editLabelSelectModal.hide();
                        
                        // 少し遅延させてからラベル編集モーダルを表示
                        setTimeout(() => {
                            editLabelById(labelId, labelName, labelColor);
                        }, 150);
                    });
                }
                
                editLabelList.appendChild(listItem);
            });
        }
        
        editLabelSelectModal.show();
    }
    
    // ラベル編集
    function editLabelById(labelId, labelName, labelColor) {
        editingLabelId = labelId;
        document.getElementById('labelModalLabel').textContent = 'ラベルを編集';
        document.getElementById('labelName').value = labelName;
        document.getElementById('labelColor').value = labelColor;
        labelModal.show();
    }
    
    // ラベル保存ボタン
    const saveLabelBtn = document.getElementById('saveLabelBtn');
    // 既存のイベントリスナーを解除（多重登録防止）
    if (saveLabelBtn._labelSaveHandler) {
        saveLabelBtn.removeEventListener('click', saveLabelBtn._labelSaveHandler);
    }
    // 新しいハンドラを定義
    const labelSaveHandler = function() {
        const name = document.getElementById('labelName').value.trim();
        const color = document.getElementById('labelColor').value;
        
        if (!name) {
            alert('ラベル名を入力してください。');
            return;
        }
        
        this.disabled = true;
        this.textContent = '保存中...';
        
        const url = editingLabelId ? `/annotator/api/labels/${editingLabelId}/` : '/annotator/api/labels/';
        const method = editingLabelId ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                name: name,
                color: color
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('!!!Label save response:', data);
            if (data.status === 'success') {
                if (editingLabelId) {
                    updateLabelInUI(data.label);
                    // アノテーションキャンバスのラベルデータも更新
                    updateLabelInCanvas(data.label);
                    alert('ラベルが更新されました');
                } else {
                    addLabelToUI(data.label);
                    // グローバルラベルデータに追加
                    window.labelsData.push(data.label);
                    alert('ラベルが作成されました');
                }
                labelModal.hide();
                // モーダルが隠れた後にbackdropをクリーンアップ
                setTimeout(() => {
                    cleanupModalBackdrops();
                }, 150);
            } else {
                alert('エラー: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('通信エラーが発生しました。もう一度お試しください。');
            // エラー時もbackdropをクリーンアップ
            cleanupModalBackdrops();
        })
        .finally(() => {
            this.disabled = false;
            this.textContent = '保存';
        });
    };
    saveLabelBtn.addEventListener('click', labelSaveHandler);
    // ハンドラをプロパティに保存しておく
    saveLabelBtn._labelSaveHandler = labelSaveHandler;
}

// UIのラベルを更新
function updateLabelInUI(label) {
    const labelButton = document.querySelector(`[data-label-id="${label.id}"]`);
    if (labelButton) {
        labelButton.setAttribute('data-label-name', label.name);
        labelButton.setAttribute('data-label-color', label.color);
        labelButton.textContent = label.name;
        labelButton.style.backgroundColor = '';
        labelButton.style.borderColor = label.color;
        
        // 選択中のラベルの場合、表示も更新
        if (labelButton.classList.contains('active')) {
            document.getElementById('selected-label').textContent = label.name;
            if (annotationCanvas) {
                annotationCanvas.selectedLabelName = label.name;
                annotationCanvas.selectedLabelColor = label.color;
            }
        }
    }
}

// UIにラベルを追加
function addLabelToUI(label) {
    const labelButtons = document.getElementById('label-buttons');
    const button = document.createElement('button');
    button.className = 'btn btn-outline-primary btn-sm me-2 mb-2 label-btn editable-label';
    button.setAttribute('data-label-id', label.id);
    button.setAttribute('data-label-name', label.name);
    button.setAttribute('data-label-color', label.color);
    button.setAttribute('title', 'クリックで編集');
    button.textContent = label.name;
    button.style.borderColor = label.color;
    
    labelButtons.appendChild(button);
}

// アノテーションキャンバスのラベルデータを更新
function updateLabelInCanvas(label) {
    const labelIndex = window.labelsData.findIndex(l => l.id === label.id);
    if (labelIndex !== -1) {
        window.labelsData[labelIndex] = label;
    }
    
    // 既存のアノテーションのラベル情報も更新
    if (annotationCanvas) {
        annotationCanvas.annotations.forEach(annotation => {
            if (annotation.label_id === label.id) {
                annotation.label_name = label.name;
                annotation.label_color = label.color;
            }
        });
        annotationCanvas.redraw();
        annotationCanvas.updateAnnotationsList();
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

// モーダルのbackdropをクリーンアップする関数
function cleanupModalBackdrops() {
    // すべてのモーダルbackdropを削除
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => {
        backdrop.remove();
    });
    
    // body要素からmodal-openクラスを削除
    document.body.classList.remove('modal-open');
    
    // bodyのstyleをリセット（overflowなど）
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    // 念のため、CSSクラスでもクリーンアップ
    document.body.classList.add('modal-backdrop-cleanup');
    setTimeout(() => {
        document.body.classList.remove('modal-backdrop-cleanup');
    }, 100);
    
    // 開いているモーダルがある場合は閉じる
    const openModals = document.querySelectorAll('.modal.show');
    openModals.forEach(modal => {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }
    });
}

// ページ離脱時やリサイズ時の cleanup
window.addEventListener('beforeunload', function() {
    cleanupModalBackdrops();
});

window.addEventListener('resize', function() {
    // リサイズ時にもbackdropの問題が起こることがあるのでクリーンアップ
    const backdrops = document.querySelectorAll('.modal-backdrop');
    if (backdrops.length > 1) {
        cleanupModalBackdrops();
    }
});

// キーボードイベント（ESCキー）でもクリーンアップ
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        setTimeout(() => {
            cleanupModalBackdrops();
        }, 200);
    }
});

// 既存のアノテーションを読み込み
annotationCanvas.loadExistingAnnotations(window.existingAnnotations);

// 既存のラベルボタンに色を適用
initializeLabelButtonColors();

// ラベル管理機能を初期化
initLabelManagement();

// キーボードナビゲーション機能を追加
function initKeyboardNavigation() {
    document.addEventListener('keydown', function(event) {
        // モーダルが開いている場合は無視
        const openModals = document.querySelectorAll('.modal.show');
        if (openModals.length > 0) {
            return;
        }
        
        // 入力フィールドにフォーカスがある場合は無視
        const activeElement = document.activeElement;
        if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
            return;
        }
        
        switch(event.key) {
            case 'ArrowLeft':
                event.preventDefault();
                const prevBtn = document.getElementById('prev-btn');
                if (prevBtn) {
                    prevBtn.click();
                }
                break;
                
            case 'ArrowRight':
                event.preventDefault();
                const nextBtn = document.getElementById('next-btn');
                if (nextBtn) {
                    nextBtn.click();
                }
                break;
                
            case 's':
            case 'S':
                if (event.ctrlKey) {
                    event.preventDefault();
                    const saveBtn = document.getElementById('save-btn');
                    if (saveBtn) {
                        saveBtn.click();
                    }
                }
                break;
        }
    });
}

// キーボードナビゲーションを初期化
initKeyboardNavigation();
