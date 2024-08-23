function getHeaders() {
  if ($("#shift-select").val() == 1) {
    headers = [
      "Loader",
      "Material",
      "Remarks",
      "6",
      "7",
      "8",
      "9",
      "10",
      "11",
      "12",
      "13",
      "14",
      "15",
      "16",
      "17",
      "#",
    ];
    column = [
      {
        data: "loader",
        width: "10%",
      },
      {
        data: "code_material",
      },
      {
        data: "code_material__remark",
      },
      {
        data: "a",
        width: "6%",
      },
      {
        data: "b",
        width: "6%",
      },
      {
        data: "c",
        width: "6%",
      },
      {
        data: "d",
        width: "6%",
      },
      {
        data: "e",
        width: "6%",
      },
      {
        data: "f",
        width: "6%",
      },
      {
        data: "g",
        width: "6%",
      },
      {
        data: "h",
        width: "6%",
      },
      {
        data: "i",
        width: "6%",
      },
      {
        data: "j",
        width: "6%",
      },
      {
        data: "k",
        width: "6%",
      },
      {
        data: "l",
        width: "6%",
      },
      {
        data: "action",
        width: "3%",
      },
    ];
  } else {
    headers = [
      "Loader",
      "Material",
      "Remarks",
      "18",
      "19",
      "20",
      "21",
      "22",
      "23",
      "0",
      "1",
      "2",
      "3",
      "4",
      "5",
      "6",
      "#",
    ];
    column = [
      {
        data: "loader",
        width: "10%",
      },
      {
        data: "code_material",
      },
      {
        data: "code_material__remark",
      },
      {
        data: "a",
        width: "6%",
      },
      {
        data: "b",
        width: "6%",
      },
      {
        data: "c",
        width: "6%",
      },
      {
        data: "d",
        width: "6%",
      },
      {
        data: "e",
        width: "6%",
      },
      {
        data: "f",
        width: "6%",
      },
      {
        data: "g",
        width: "6%",
      },
      {
        data: "h",
        width: "6%",
      },
      {
        data: "i",
        width: "6%",
      },
      {
        data: "j",
        width: "6%",
      },
      {
        data: "k",
        width: "6%",
      },
      {
        data: "l",
        width: "6%",
      },
      {
        data: "m",
        width: "6%",
      },
      {
        data: "action",
        width: "3%",
      },
    ];
  }
  column.forEach(function (c) {
    c.render = function (data) {
      return data == 0 || data == "nan" ? "" : data;
    };
  });
}

function getHeadersLoader() {
  if ($("#shift-select").val() == 1) {
    headers = [
      "Loader",
      "Hauler",
      "Material",
      "Remarks",
      "6",
      "7",
      "8",
      "9",
      "10",
      "11",
      "12",
      "13",
      "14",
      "15",
      "16",
      "17",
      "#",
    ];
    column = [
      {
        data: "loader",
        width: "10%",
      },
      {
        data: "hauler",
        width: "10%",
      },
      {
        data: "code_material",
      },
      {
        data: "code_material__remark",
      },
      {
        data: "a",
        width: "6%",
      },
      {
        data: "b",
        width: "6%",
      },
      {
        data: "c",
        width: "6%",
      },
      {
        data: "d",
        width: "6%",
      },
      {
        data: "e",
        width: "6%",
      },
      {
        data: "f",
        width: "6%",
      },
      {
        data: "g",
        width: "6%",
      },
      {
        data: "h",
        width: "6%",
      },
      {
        data: "i",
        width: "6%",
      },
      {
        data: "j",
        width: "6%",
      },
      {
        data: "k",
        width: "6%",
      },
      {
        data: "l",
        width: "6%",
      },
      {
        data: "action",
        width: "3%",
      },
    ];
  } else {
    headers = [
      "Loader",
      "Hauler",
      "Material",
      "Remarks",
      "18",
      "19",
      "20",
      "21",
      "22",
      "23",
      "0",
      "1",
      "2",
      "3",
      "4",
      "5",
      "6",
      "#",
    ];
    column = [
      {
        data: "loader",
        width: "10%",
      },
      {
        data: "hauler",
        width: "10%",
      },
      {
        data: "code_material",
      },
      {
        data: "code_material__remark",
      },
      {
        data: "a",
        width: "6%",
      },
      {
        data: "b",
        width: "6%",
      },
      {
        data: "c",
        width: "6%",
      },
      {
        data: "d",
        width: "6%",
      },
      {
        data: "e",
        width: "6%",
      },
      {
        data: "f",
        width: "6%",
      },
      {
        data: "g",
        width: "6%",
      },
      {
        data: "h",
        width: "6%",
      },
      {
        data: "i",
        width: "6%",
      },
      {
        data: "j",
        width: "6%",
      },
      {
        data: "k",
        width: "6%",
      },
      {
        data: "l",
        width: "6%",
      },
      {
        data: "m",
        width: "6%",
      },
      {
        data: "action",
        width: "3%",
      },
    ];
  }
  column.forEach(function (c) {
    c.render = function (data, type, row, meta) {
      return data == 0 || data == "nan" ? "" : data;
    };
  });
}

function handleInputChange(form, label_button) {
  // Check if the button already exists
  if (
    !form.select("button#save-button").node() &&
    !form.select("button#cancel-button").node()
  ) {
    // Add a button at the bottom of the card
    var cardFooter = form
      .append("div")
      .attr("class", "mb-0 mt-2 row d-flex justify-content-end");
    cardFooter
      .append("button")
      .attr("id", "cancel-button")
      .attr("type", "button")
      .attr("class", "btn btn-secondary me-3")
      .attr("style", "width: auto")
      .text("Cancel")
      .on("click", function () {
        load();
      });
    cardFooter
      .append("button")
      .attr("id", "save-button")
      .attr("type", "submit")
      .attr("class", "btn btn-primary")
      .attr("style", "width: auto")
      .text(label_button)
      .on("click", function () {
        setTimeout(function () {
          // Remove the cardFooter after submission
          cardFooter.remove();
          load();
        }, 1000);
      });
  }
}

function addRow(button) {
  $.ajax({
    url: addUrl,
    type: "POST",
    headers: {
      "X-CSRFToken": csrf_token,
    },
    data: {
      date: $("#date-select").val(),
      shift: $("#shift-select").val(),
      hauler: $("#cn-hauler").val(),
      id: button.getAttribute("data-id"),
    },
    complete: function () {
      loadTable();
    },
  });
}

function addRowLoader() {
  $.ajax({
    url: addLoaderUrl,
    type: "POST",
    headers: {
      "X-CSRFToken": csrf_token,
    },
    data: {
      date: $("#date-select").val(),
      shift: $("#shift-select").val(),
    },
    success: function () {
      loadTable();
    },
  });
}

function loadTable() {
  tables.forEach(function (table) {
    table.draw();
  });
}

function deleteRow(button) {
  $.ajax({
    url: deleteUrl,
    type: "POST",
    headers: {
      "X-CSRFToken": csrf_token,
    },
    data: {
      id: button.getAttribute("data-id"),
    },
    complete: function () {
      loadTable();
    },
  });
}

function loadWh() {
  $.ajax({
    url: whUrl,
    type: "POST",
    data: {
      date: $("#date-select").val(),
      shift: $("#shift-select").val(),
      hauler: $("#cn-hauler").val().toString(),
    },
    headers: {
      "X-CSRFToken": csrf_token,
    },
    success: function (data) {
      var wh = data.data.durasi.WH;
      var hm = $("#HM").val();
      $("#WH").val(wh.toFixed(2));

      if (wh > hm) {
        d3.select("#WH").classed("bg-warning", true);
      } else {
        d3.select("#WH").classed("bg-warning", false);
      }
    },
    error: function (error) {
      console.error(error);
    },
  });
}

function get_options(callback) {
  $.ajax({
    url: optionsUrl,
    type: "GET",
    dataType: "json",
    success: function (data) {
      var materials = processOptions(data.materials);
      var loaders = processOptions(data.loaders);
      if (callback) {
        callback(loaders, materials);
      }
    },
    error: function (error) {
      console.error(error);
    },
  });
}

function processOptions(opts) {
  return opts.map((opt) => ({ label: opt }));
}
