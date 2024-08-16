// formHandler.js
function populateUpdateForm(modal, d) {
  var startHour = new Date(d.starting_time).getHours();
  var startMinute = new Date(d.starting_time).getMinutes();
  var startSecond = new Date(d.starting_time).getSeconds();
  modal
    .find(".modal-title")
    .text("Update Data - " + d.unit + " - id: " + d.database_id);
  modal.find("input[name=unit]").val(d.unit);
  modal.find("input[name=date]").val($("#date-select").val());
  modal.find("input[name=hour]").val($("#hour-select").val());
  modal
    .find("input[name=timestart]")
    .val(toDateString(d.starting_time).slice(-8));
  modal.find("input[name=timeend]").val(toDateString(d.ending_time).slice(-8));
  modal.find("input[name=database_id]").val(d.database_id);
  modal.find("input[name=stb]").val(d.label);
  modal
    .find("input[name=duration]")
    .val(((d.ending_time - d.starting_time) / 60000).toFixed(2));

  if (
    (startMinute === 0 && startSecond === 0) ||
    (startHour === 6 && startMinute === 30 && startSecond === 0)
  ) {
    modal.find("#deleteButton").prop("disabled", true);
  } else {
    modal.find("#deleteButton").prop("disabled", false);
  }
}

function populateAddForm(modal) {
  modal.find(".modal-title").text("Add Data STB - " + data_unit);
  modal.find("input[name=timestart]").val(data_time.slice(-8));
  modal.find("input[name=database_id]").val(data_databese_id);
  modal.find("input[name=stb]").val("");
}

function populateDeleteForm(modal) {
  var db_id = $("#updateModal").find("input[name=database_id]").val();
  var stb = $("#updateModal").find("input[name=stb]").val();
  modal.find("input[name=database_id_delete]").val(db_id);
  modal
    .find(".p-item")
    .html("Anda yakin ingin menghapus data <b>" + stb + "</b> ini?");
}

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

function handleSplitSubmission(
  url,
  dataUnit,
  data_databese_id,
  data_time,
  token
) {
  $.ajax({
    url: url,
    type: "POST",
    data: {
      database_id: data_databese_id,
      timestart: data_time,
    },
    headers: {
      "X-CSRFToken": token,
    },
    success: function (response, status, xhr) {
      if (xhr.status === 204) {
        // Check if the status code is 204
        showDetail(dataUnit);
      }
    },
    error: function (xhr, status, error) {
      console.error("Form submission failed:", error);
    },
  });
}

function focusAndSelectInput() {
  var input = $("#stb-label");
  if (input) {
    input.focus();
    input.select();
  }
}
