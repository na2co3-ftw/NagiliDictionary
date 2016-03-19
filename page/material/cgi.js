//


$(function () {
  setup();
});

function setup() {
  $("[name=\"search\"]").on("keydown", function (event) {
    if (event.which == 13) {
      url = submit_url() + "submit=検索";
      location.href = url;
      return false;
    }
  });
  $("[name=\"search_mana\"]").on("keydown", function (event) {
    if (event.which == 13) {
      url = submit_url() + "submit_mana=検索";
      location.href = url;
      return false;
    }
  });
}

function submit_url() {
  url = "nagili.cgi?";
  url += "mode=search&";
  url += "search=" + encodeURIComponent($("[name=\"search\"]").val()) + "&";
  url += "type=" + $("[name=\"type\"]:checked").val() + "&";
  url += "agree=" + $("[name=\"agree\"]:checked").val() + "&";
  if ($("[name=\"random\"]:checked").val()) {
    url += "random=1&";
  }
  url += "search_mana=" + encodeURIComponent($("[name=\"search_mana\"]").val()) + "&";
  url += "type_mana=" + $("[name=\"type_mana\"]:checked").val() + "&";
  return url;
}