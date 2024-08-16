function setTimeFrameShiftly() {
  var ts_shift1 = toTimestamp($("#date-select").val() + " 06:30");
  var te_shift1 = toTimestamp($("#date-select").val() + " 18:00");

  var ts_shift2 = toTimestamp($("#date-select").val() + " 18:00");
  var te_shift2 = new Date($("#date-select").val());
  te_shift2.setDate(te_shift2.getDate() + 1);
  te_shift2.setHours(6, 30);

  if ($("#shift-select").val() == 1) {
    ts = ts_shift1;
  } else {
    ts = ts_shift2;
  }
  if ($("#shift-select").val() == 1) {
    te = te_shift1;
  } else {
    te = te_shift2;
  }
}

function getColorData() {
  var colorDict = {
    BS: "red",
    BUS: "red",
    BA: "red",
    S1: "#32994e",
    S2: "#2c4d34",
    S3: "#212121",
    S4: "#212121",
    S5A: "#d1854f",
    S5B: "#d1854f",
    S5C: "#d1854f",
    S6: "orange",
    S7: "#212121",
    S8: "pink",
    S9: "#6e3299",
    S10A: "#lightgreen",
    S10B: "lightgreen",
    S11: "#fae637",
    S12: "lightgrey",
    S13: "#212121",
    S14A: "#f3c3fa",
    S14B: "#f3c3fa",
    S14C: "#f3c3fa",
    S15: "gold",
    S17: "#212121",
    S18: "#4287f5",
    S19: "#f06d16",
    S20C: "#a7f2bb",
    "WH OB": "#212121",
    WH: "#07cceb",
    "WH GEN": "darkblue",
    I: "grey",
    O: "green",
    M: "blue",
    G: "pink",
    T: "brown",
    TD: "brown",
    C: "black",
  };

  var colorScale = d3.scale
    .ordinal()
    .domain(Object.keys(colorDict))
    .range(Object.values(colorDict));

  return colorScale;
}

function toTimestamp(strDate) {
  var datum = Date.parse(strDate);
  return datum;
}

function toDateString(timestamp) {
  var date = new Date(timestamp);
  var options = {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  };
  return date.toLocaleString("en-GB", options);
}

var Tooltip = d3
  .select(".pc-content")
  .append("div")
  .style("opacity", 0)
  .attr("class", "tooltip")
  .style("position", "absolute")
  .style("background-color", "white")
  .style("border", "solid")
  .style("border-width", "2px")
  .style("border-radius", "5px")
  .style("padding", "5px");

$(".pc-content").on("mousemove", function (e) {
  var pcContentOffset = $(this).offset();
  var mouseX = e.pageX - pcContentOffset.left + 10;
  var mouseY = e.pageY - pcContentOffset.top + 10;
  $(".tooltip").css({
    left: mouseX,
    top: mouseY,
  });
});

document.onclick = hideMenu;
document.oncontextmenu = rightClick;

function hideMenu() {
  $("#customContextMenu").hide();
}

function rightClick(e) {
  if ($(e.target).closest("#table-card").length > 0) {
    e.preventDefault();
    data_time = _data_time;
    Tooltip.style("opacity", 0);
    $("#customContextMenu")
      .css({
        left: e.pageX,
        top: e.pageY,
      })
      .show();
  }
}
