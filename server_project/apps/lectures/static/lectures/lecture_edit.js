const loadedFolders = new Set(); // Track loaded folders to avoid redundant AJAX calls

function collapseFolder(folderId) {
    const icon = document.getElementById(`collapse-icon-${folderId}`);
    const content = document.getElementById(`collapse-${folderId}`);

    // Toggle folder open/close icon
    icon.classList.toggle('bi-chevron-right');
    icon.classList.toggle('bi-chevron-down');

    // If data is already loaded, just toggle visibility
    if (loadedFolders.has(folderId)) {
        return;
    }

    $.ajax({
        url: GET_ITEMS_URL,
        type: 'POST',
        data: {
            'csrfmiddlewaretoken': CSRF_TOKEN,
            'folder-id': folderId,
        },
        success: function (data) {
            if (data["subfolders"].length + data["database"].length === 0) {
                content.innerHTML = '<li class="d-flex align-items-center mb-2">No items</li>';
            } else {
                data["subfolders"].forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.className = 'd-flex align-items-center mb-2';

                    const chevronIcon = document.createElement('i');
                    chevronIcon.className = 'bi bi-chevron-right me-2';
                    chevronIcon.setAttribute('data-bs-toggle', 'collapse');
                    chevronIcon.setAttribute('href', `#collapse-${item.id}`);
                    chevronIcon.id = `collapse-icon-${item.id}`;
                    chevronIcon.setAttribute('role', 'button');
                    chevronIcon.onclick = () => collapseFolder(item.id);

                    const folderIcon = document.createElement('i');
                    folderIcon.className = 'bi bi-folder me-2';

                    const textNode = document.createTextNode(item.name);

                    const subList = document.createElement('ul');
                    subList.className = 'list-unstyled ms-4 collapse';
                    subList.id = `collapse-${item.id}`;

                    listItem.appendChild(chevronIcon);
                    listItem.appendChild(folderIcon);
                    listItem.appendChild(textNode);
                    content.appendChild(listItem);
                    content.appendChild(subList);
                });

                data["database"].forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.className = 'd-flex align-items-center mb-2';

                    const img = document.createElement('img');
                    img.src = GET_THUMBNAIL_URL.replace('0', item.id);
                    img.height = 40;
                    img.className = 'me-2';
                    img.alt = '';

                    const textNode = document.createTextNode(item.name);

                    const addButton = document.createElement('button');
                    addButton.className = 'btn btn-sm ms-auto';
                    addButton.setAttribute('title', 'Add');
                    addButton.onclick = () => addContent(item.id, item.name);

                    const icon = document.createElement('i');
                    icon.className = 'bi bi-plus-circle';

                    addButton.appendChild(icon);
                    listItem.appendChild(img);
                    listItem.appendChild(textNode);
                    listItem.appendChild(addButton);
                    content.appendChild(listItem);
                });

                // Mark folder as loaded to prevent redundant AJAX calls
                loadedFolders.add(folderId);
            }
        },
        error: function (message) {
            showFeedback(message, "danger")
        }
    });
}

function addContent(slideId, slideName) {
    const contentsList = document.getElementById('contents-list');

    const existingSlides = Array.from(contentsList.getElementsByClassName('slide-id'));
    if (existingSlides.some(slide => slide.value === slideId.toString())) {
        showFeedback(`Slide "${slideName}" is already added!`, "warning");
        return;
    }

    const content = document.createElement('li');
    content.className = 'list-group-item d-flex align-items-center';

    // Create move buttons
    const moveContainer = document.createElement('div');
    moveContainer.className = 'd-flex flex-column me-2';

    const upBtn = document.createElement('i');
    upBtn.className = 'bi bi-caret-up';
    upBtn.setAttribute('role', 'button');
    upBtn.onclick = function () {
        moveContentUp(this);
    };

    const downBtn = document.createElement('i');
    downBtn.className = 'bi bi-caret-down';
    downBtn.setAttribute('role', 'button');
    downBtn.onclick = function () {
        moveContentDown(this);
    };

    moveContainer.appendChild(upBtn);
    moveContainer.appendChild(downBtn);

    // Create slide image
    const img = document.createElement('img');
    img.src = GET_THUMBNAIL_URL.replace("0", slideId);
    img.height = 40;
    img.className = 'me-2';
    img.alt = '';

    // Hidden input for slide ID
    const slideIdInput = document.createElement('input');
    slideIdInput.type = 'hidden';
    slideIdInput.className = 'slide-id';
    slideIdInput.value = slideId;

    // Slide name
    const slideText = document.createTextNode(slideName);

    // Annotation selection
    const annotationContainer = document.createElement('div');
    annotationContainer.className = 'ms-auto col-3';

    const annotationIdInput = document.createElement('input');
    annotationIdInput.type = 'hidden';
    annotationIdInput.className = 'annotation-id';

    const annotationSelect = document.createElement('select');
    annotationSelect.className = 'form-select';
    annotationSelect.onclick = function () {
        setupSlideAnnotation(this, slideId);
    };
    annotationSelect.onchange = function () {
        updateAnnotationId(this);
    };

    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'None';
    defaultOption.selected = true;

    annotationSelect.appendChild(defaultOption);
    annotationContainer.appendChild(annotationIdInput);
    annotationContainer.appendChild(annotationSelect);

    // Remove button
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-sm';
    removeBtn.setAttribute('title', 'Remove');
    removeBtn.onclick = function () {
        removeContent(this);
    };

    const removeIcon = document.createElement('i');
    removeIcon.className = 'bi bi-dash-circle';

    removeBtn.appendChild(removeIcon);

    // Append everything to <li>
    content.appendChild(moveContainer);
    content.appendChild(img);
    content.appendChild(slideIdInput);
    content.appendChild(slideText);
    content.appendChild(annotationContainer);
    content.appendChild(removeBtn);

    contentsList.appendChild(content);
}


function removeContent(element) {
    const li = element.closest('li');
    if (li) {
        li.remove();
    }
}

function moveContentUp(element) {
    let listItem = element.closest('li');
    let prevItem = listItem.previousElementSibling;

    if (prevItem) {
        listItem.parentNode.insertBefore(listItem, prevItem);
    }
}

function moveContentDown(element) {
    let listItem = element.closest('li');
    let nextItem = listItem.nextElementSibling;

    if (nextItem) {
        listItem.parentNode.insertBefore(nextItem, listItem);
    }
}

const loadedSlideAnnotations = new Map(); // Stores fetched annotations per slide

function setupSlideAnnotation(element, slideId) {
    const select = element.closest('select');

    // Prevent redundant requests
    if (loadedSlideAnnotations.has(slideId)) {
        return;
    }

    $.ajax({
        url: GET_SLIDE_ANNOTATIONS_URL,
        type: 'POST',
        data: {
            'csrfmiddlewaretoken': CSRF_TOKEN,
            'slide-id': slideId,
        },
        success: function (data) {
            if (!data["annotations"].length) return;

            const existingOptions = new Set(Array.from(select.options).map(option => option.value));

            data["annotations"].forEach(item => {
                if (!existingOptions.has(item.id.toString())) {
                    const annotation = document.createElement('option');
                    annotation.value = item.id;
                    annotation.textContent = `${item.name} - ${item.author}`;
                    select.appendChild(annotation);
                }
            });

            // Mark this slide's annotations as loaded
            loadedSlideAnnotations.set(slideId, true);
        },
        error: function (message) {
            showFeedback(message, "danger")
        }
    });
}

function updateAnnotationId(element) {
    const annotationIdInput = element.closest('li').querySelector('.annotation-id');
    annotationIdInput.value = element.value;
}

function submitLectureChanges(lectureId) {
    const name = document.getElementById('lecture-name').value;
    const description = document.getElementById('lecture-description').value;

    // Get all checked groups (both Publisher and Viewer)
    const selectedGroups = Array.from(document.querySelectorAll('input[name="publisher-groups"]:checked, input[name="viewer-groups"]:checked'))
        .map(checkbox => checkbox.value);

    // Get contents list
    const list = document.getElementById('contents-list').getElementsByTagName('li');
    let contents = [];
    Array.from(list).forEach(function (content, i) {
        const order = i + 1;
        const slideId = content.getElementsByClassName('slide-id')[0].value;
        const annotationId = content.getElementsByClassName('annotation-id')[0].value;

        contents.push({
            'order': order,
            'slide_id': slideId,
            'annotation_id': annotationId,
        });
    });

    // Send data via AJAX
    $.ajax({
        url: EDIT_LECTURE_URL,
        type: 'POST',
        data: {
            'csrfmiddlewaretoken': CSRF_TOKEN,
            'lecture-id': lectureId,
            'name': name,
            'description': description,
            'groups': JSON.stringify(selectedGroups),  // Send all selected groups in one list
            'contents': JSON.stringify(contents),
        },
        success: function () {
            showFeedback("Lecture updated successfully!", "success");
        },
        error: function (message) {
            showFeedback(message, "danger");
        }
    });
}

