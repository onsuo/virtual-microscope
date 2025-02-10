function setupLectureDetail(lectureId) {
    fetch(LECTURE_DETAIL_URL, {
        method: 'POST',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        body: JSON.stringify({
            lecture_id: lectureId,
        }),
    })
        .then(response => response.json())
        .then(data => {
            document.getElementById('detail-lecture-name').textContent = data['name'];
            document.getElementById('detail-lecture-description').textContent = data['description'] || '-';
            document.getElementById('detail-lecture-contents').textContent = data['slides_count'] + ' database';
            document.getElementById('detail-lecture-author').textContent = data['author'] || '-';
            document.getElementById('detail-lecture-groups').textContent = data['groups'];
            document.getElementById('detail-lecture-activity').textContent = data['is_active'] ? 'On' : 'Off';
            document.getElementById('detail-lecture-created').textContent = data['created_at'];
            document.getElementById('detail-lecture-updated').textContent = data['updated_at'];
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function toggleLectureActivity(lectureId) {
    $.ajax({
        url: TOGGLE_LECTURE_ACTIVITY_URL,
        type: 'POST',
        data: {
            'csrfmiddlewaretoken': CSRF_TOKEN,
            'lecture-id': lectureId,
        },
        success: function (data) {
            const icon = document.getElementById('lecture-activity-icon-' + lectureId);
            const updated = document.getElementById('lecture-updated-' + lectureId);

            if (data['is_active']) {
                icon.classList.remove('bi-toggle-off');
                icon.classList.add('bi-toggle-on');
                icon.nextSibling.textContent = ' On ';
            } else {
                icon.classList.remove('bi-toggle-on');
                icon.classList.add('bi-toggle-off');
                icon.nextSibling.textContent = ' Off ';
            }
            updated.textContent = data['updated_at'];
        }
    });
}