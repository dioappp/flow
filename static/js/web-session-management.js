$("#date-select").on("change", function () {
  sessionStorage.setItem("dateVal", $(this).val());
});
$("#hour-select").on("change", function () {
  sessionStorage.setItem("hourVal", $(this).val());
});
$("#shift-select").on("change", function () {
  sessionStorage.setItem("shiftVal", $(this).val());
});

shift = 1;
const d = new Date();

if (d.getMinutes() < 17) {
  d.setHours(d.getHours() - 2);
} else {
  d.setHours(d.getHours() - 1);
}

let hour = d.getHours();

var dd = String(d.getDate()).padStart(2, "0");
var mm = String(d.getMonth() + 1).padStart(2, "0"); //January is 0!
var yyyy = d.getFullYear();

today = yyyy + "-" + mm + "-" + dd;

const savedHourVal = sessionStorage.getItem("hourVal");
if (savedHourVal) {
  $("#hour-select").val(savedHourVal);
} else {
  $("#hour-select").val(hour);
}

const savedDateVal = sessionStorage.getItem("dateVal");
if (savedDateVal) {
  $("#date-select").val(savedDateVal);
} else {
  $("#date-select").val(today);
}

const savedShiftVal = sessionStorage.getItem("shiftVal");
if (savedShiftVal) {
  $("#shift-select").val(savedShiftVal);
} else {
  $("#shift-select").val(shift);
}
