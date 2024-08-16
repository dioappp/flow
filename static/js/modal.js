// formHandler.js
function handleUpdateFormSubmission(url, dataUnit, formData) {
  // Enable disabled fields if needed
  $("#timeend-label, #duration-label").prop("disabled", false);

  $.ajax({
    type: "POST",
    url: url,
    data: formData,
    processData: false,
    contentType: false,
    success: function (response, status, xhr) {
      if (xhr.status === 204) {
        // Check if the status code is 204
        $("#updateModal").modal("hide");
        showDetail(dataUnit);
      }
    },
    error: function (xhr, status, error) {
      console.error("Form submission failed:", error);
    },
  });

  // Re-disable the fields if they were enabled
  $("#timeend-label, #duration-label").prop("disabled", true);
}

function handleAddFormSubmission(url, dataUnit, formData) {
  $.ajax({
    type: "POST",
    url: url,
    data: formData,
    processData: false,
    contentType: false,
    success: function (response, status, xhr) {
      if (xhr.status === 204) {
        // Check if the status code is 204
        $("#addModal").modal("hide");
        showDetail(dataUnit);
      }
    },
    error: function (response, status, error) {
      console.error("Form submission failed:", error);
    },
  });
}

function handleDeleteSubmission(url, dataUnit, formData) {
  formData.append("delete", "delete");

  $.ajax({
    type: "POST",
    url: url,
    data: formData,
    processData: false,
    contentType: false,
    success: function (response, status, xhr) {
      if (xhr.status === 204) {
        // Check if the status code is 204
        $("#confirmModal").modal("hide");
        showDetail(dataUnit);
      }
    },
    error: function (xhr, status, error) {
      console.error("Form submission failed:", error);
    },
  });
}
