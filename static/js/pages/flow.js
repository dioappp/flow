$('#date-select').on('change',function(){
  sessionStorage.setItem('dateVal',$(this).val())
})
$('#hour-select').on('change',function(){
  sessionStorage.setItem('hourVal',$(this).val())
})
$('#shift-select').on('change',function(){
  sessionStorage.setItem('shiftVal',$(this).val())
})

$(document).on('mousemove', function(e) {
  $('.tooltip').css({
    'left': e.pageX-100,
    'top': e.pageY-135,
  });
});

document.onclick = hideMenu;
document.oncontextmenu = rightClick;

function hideMenu() {
  $('#customContextMenu').hide();
}

function rightClick(e) {
  e.preventDefault();
  data_time = _data_time
  Tooltip.style("opacity",0);
  $('#customContextMenu').css({ left: e.pageX-100, top: e.pageY-135}).show();

}
shift = 1
const d = new Date()

if(d.getMinutes() < 17){
  d.setHours(d.getHours() - 2);
} else {
  d.setHours(d.getHours() - 1);
}

let hour = d.getHours();

var dd = String(d.getDate()).padStart(2, "0");
var mm = String(d.getMonth() + 1).padStart(2, "0"); //January is 0!
var yyyy = d.getFullYear();

today = yyyy + "-" + mm + "-" + dd;

const savedHourVal = sessionStorage.getItem('hourVal');
if (savedHourVal){
  $("#hour-select").val(savedHourVal);
} else {
  $("#hour-select").val(hour);
}

const savedDateVal = sessionStorage.getItem('dateVal');
if (savedDateVal){
  $("#date-select").val(savedDateVal);
} else {
  $("#date-select").val(today);
}

const savedShiftVal = sessionStorage.getItem('shiftVal');
if (savedShiftVal){
  $("#shift-select").val(savedShiftVal);
} else {
  $("#shift-select").val(shift);
}

setTimeFrameShiftly()

var Tooltip = d3.select("#main-area")
  .append("div")
  .style("opacity", 0)
  .attr("class", "tooltip")
  .style("background-color", "white")
  .style("border", "solid")
  .style("border-width", "2px")
  .style("border-radius", "5px")
  .style("padding", "5px");

function toTimestamp(strDate) {
  var datum = Date.parse(strDate);
  return datum;
}

function toDateString(timestamp) {
  var date = new Date(timestamp);
  var options = { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' };
  return date.toLocaleString('en-GB', options);
}

function exportExcel(){
  var date = $("#date-select").val();
  var shift = $("#shift-select").val();
  $("#exportDate").val(date);
  $("#exportShift").val(shift);
  $("#exportForm").submit();
}

$('#addModal').on('show.bs.modal', function(event) {
  var modal = $(this);
  modal.find('.modal-title').text('Add Data STB - ' + data_unit);
  modal.find('input[name=timestart]').val(data_time.slice(-8));
  modal.find('input[name=database_id]').val(data_databese_id);
  modal.find('input[name=stb]').val('');
});

$('#confirmModal').on('show.bs.modal', function (event) {
  var modal = $(this);
  var db_id = $('#updateModal').find('input[name=database_id]').val();
  var stb = $('#updateModal').find('input[name=stb]').val();
  modal.find('input[name=database_id_delete]').val(db_id);
  modal.find('.p-item').html("Anda yakin ingin menghapus data <b>" + stb +"</b> ini?");
});

width = 1400;

var colorDict = {
  "BS":"red",
  "BUS":"red",
  "BA":"red",
  "S1":"#32994e",
  "S2":"#2c4d34",
  "S3":"#212121",
  "S4":"#212121",
  "S5A":"#d1854f",
  "S5B":"#d1854f",
  "S5C":"#d1854f",
  "S6":"orange",
  "S7":"#212121",
  "S8":"pink",
  "S9":"#6e3299",
  "S10A":"#lightgreen",
  "S10B":"lightgreen",
  "S11":"#fae637",
  "S12":"lightgrey",
  "S13":"#212121",
  "S14A":"#f3c3fa",
  "S14B":"#f3c3fa",
  "S14C":"#f3c3fa",
  "S15":"gold",
  "S17":"#212121",
  "S18":"#4287f5",
  "S19":"#f06d16",
  "S20C":"#a7f2bb",
  "WH OB":"#212121",
  "WH":"#07cceb",
  "WH GEN":"darkblue",
  "IPD": "grey",
  "OB": "green",
  "Mud": "blue",
  "Gen": "pink",
  "Top Soil": "brown",
  "Coal":"black",
  "General": "gold"
};

colorScale = d3.scale.ordinal()
  .domain(Object.keys(colorDict))
  .range(Object.values(colorDict));

function setTimeFrameShiftly(){
  var ts_shift1 = toTimestamp($('#date-select').val() + ' 06:30')
  var te_shift1 = toTimestamp($('#date-select').val() + ' 18:00')

  var ts_shift2 = toTimestamp($('#date-select').val() + ' 18:00')
  var te_shift2 = new Date($('#date-select').val())
  te_shift2.setDate(te_shift2.getDate() + 1)
  te_shift2.setHours(6,30)

  if ($('#shift-select').val() == 1){ts = ts_shift1} else {ts = ts_shift2}
  if ($('#shift-select').val() == 1){te = te_shift1} else {te = te_shift2}
}