function SaveAnnotation(slideId, data, annotationId = null) {
    $.ajax({
        type: "POST",
        url: SAVE_ANNOTATION_URL,
        data: {
            slideId: slideId,
            data: data,
            annotationId: annotationId
        },
        success: function (response) {
            showFeedback(response.message, "success")
        },
        error: function (response) {
            showFeedback(response.message, "danger")
        }
    });
}

function LoadAnnotationList(slideId) {
    $.ajax({
        type: "POST",
        url: LOAD_ANNOTATION_LIST_URL,
        data: {
            slideId: slideId
        },
        success: function (response) {
            const data = JSON.parse(response.data)
            console.log(data)
            for (const annotation in data) {
                const annotationItem = document.createElement("li")
                const annotationItemLink = document.createElement("a")
                annotationItemLink.href = SLIDE_VIEWER_URL.replace("0", slideId) + `?annotation=${annotation.id}`
                annotationItemLink.innerText = annotation.name
                annotationItem.appendChild(annotationItemLink)
            }
        },
        error: function (response) {
            showFeedback(response.message, "danger")
        }
    });
}