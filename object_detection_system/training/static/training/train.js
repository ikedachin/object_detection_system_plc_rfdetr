document.addEventListener('DOMContentLoaded', function() {
    const projectSelect = document.getElementById('project_name');
    const datasetYamlSelect = document.getElementById('dataset_yaml');
    const datasetYamlFullpath = document.getElementById('dataset_yaml_fullpath');
    const dataTypeSelect = document.getElementById('data_type');

    function selectedProjectName() {
        if (!projectSelect || projectSelect.selectedIndex < 0) {
            return '';
        }
        const selectedOption = projectSelect.options[projectSelect.selectedIndex];
        return selectedOption ? (selectedOption.getAttribute('data-project-name') || selectedOption.textContent.trim()) : '';
    }

    function setDatasetYamlOptions(yamls) {
        if (!datasetYamlSelect) {
            return;
        }
        datasetYamlSelect.innerHTML = '';
        if (yamls && yamls.length > 0) {
            yamls.forEach(function(yaml) {
                const opt = document.createElement('option');
                opt.value = yaml.name;
                opt.textContent = yaml.name;
                opt.setAttribute('data-fullpath', yaml.fullpath);
                datasetYamlSelect.appendChild(opt);
            });
            datasetYamlSelect.disabled = false;
            if (datasetYamlFullpath) {
                datasetYamlFullpath.value = yamls[0].fullpath;
            }
        } else {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'データセットyaml未生成';
            datasetYamlSelect.appendChild(opt);
            datasetYamlSelect.disabled = true;
            if (datasetYamlFullpath) {
                datasetYamlFullpath.value = '';
            }
        }
    }

    function updateYamlFullPath() {
        if (!datasetYamlSelect || !datasetYamlFullpath) {
            return;
        }
        if (datasetYamlSelect.selectedIndex >= 0) {
            const opt = datasetYamlSelect.options[datasetYamlSelect.selectedIndex];
            datasetYamlFullpath.value = opt.getAttribute('data-fullpath') || '';
        } else {
            datasetYamlFullpath.value = '';
        }
    }

    function refreshDatasetYamls() {
        const selectedProject = selectedProjectName();
        const dataType = dataTypeSelect ? dataTypeSelect.value : '';
        if (!selectedProject || !dataType) {
            setDatasetYamlOptions([]);
            return Promise.resolve();
        }
        return fetch(`?project_name=${encodeURIComponent(selectedProject)}&data_type=${encodeURIComponent(dataType)}`)
            .then(res => res.json())
            .then(data => {
                setDatasetYamlOptions(data.yamls || []);
            })
            .catch(() => {
                setDatasetYamlOptions([]);
            });
    }

    if (datasetYamlSelect) {
        datasetYamlSelect.addEventListener('change', updateYamlFullPath);
        updateYamlFullPath();
    }

    const generateNameBtn = document.getElementById('generateNameBtn');
    if (generateNameBtn) {
        generateNameBtn.addEventListener('click', function() {
            const projectName = selectedProjectName();
            if (projectName) {
                const now = new Date();
                const year = now.getFullYear();
                const month = String(now.getMonth() + 1).padStart(2, '0');
                const day = String(now.getDate()).padStart(2, '0');
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                const seconds = String(now.getSeconds()).padStart(2, '0');
                document.getElementById('training_name').value = `${projectName}_${year}${month}${day}_${hours}${minutes}${seconds}`;
            } else {
                document.getElementById('training_name').value = '';
            }
        });
    }

    // is_activeなプロジェクトを自動選択（サーバー側でselected付与しているが、JSでも補助）
    if (projectSelect) {
        let foundActive = false;
        for (let i = 0; i < projectSelect.options.length; i++) {
            const opt = projectSelect.options[i];
            if (opt.getAttribute('data-is-active') === 'true') {
                projectSelect.selectedIndex = i;
                foundActive = true;
                break;
            }
        }
        if (!foundActive && projectSelect.options.length > 0) {
            projectSelect.selectedIndex = 0;
        }

        projectSelect.addEventListener('change', refreshDatasetYamls);
        refreshDatasetYamls();
    }

    if (dataTypeSelect) {
        dataTypeSelect.addEventListener('change', refreshDatasetYamls);
    }

    const form = document.getElementById('trainForm');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);
        fetch('', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            const resultDiv = document.getElementById('trainResult');
            if (data.success) {
                resultDiv.innerHTML = `<div class='alert alert-success'>学習が完了しました。<br>モデル: ${data.model_path}<br>メトリクス: ${JSON.stringify(data.metrics)}</div>`;
            } else {
                resultDiv.innerHTML = `<div class='alert alert-danger'>エラー: ${data.error}</div>`;
            }
        })
        .catch(err => {
            document.getElementById('trainResult').innerHTML = `<div class='alert alert-danger'>通信エラー: ${err}</div>`;
        });
    });
});
