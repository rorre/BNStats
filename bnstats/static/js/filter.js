$(function () {
    $('select.dropdown').dropdown()
})

$("#applyButton").click(function () {
    var filters = $("#filterSelect").serializeArray()
    if (filters.length == 0) return

    $("tbody > tr").hide()

    var filteredObjects = []
    var lastFilter = ""
    var result;

    for (var i = 0; i < filters.length; i++) {
        var filterName = filters[i]["value"]
        if (filters[i]["name"] != lastFilter) {
            filteredObjects.push(result)
            result = []
        }
        result = result.concat($("tbody > tr:contains('" + filterName + "')").toArray())
        lastFilter = filters[i]["name"]
    }
    filteredObjects.push(result)

    var endResult = filteredObjects[1]
    for (var i = 2; i < filteredObjects.length; i++) {
        endResult = endResult.filter(function (v) {
            return filteredObjects[i].indexOf(v) != -1
        })
    }

    endResult.forEach(function (v) {
        $(v).show()
    })
})

$("#resetButton").click(function () {
    $(".dropdown").dropdown('clear')
    $("tbody > tr").show()
})