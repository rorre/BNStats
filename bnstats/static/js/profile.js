/// <reference path="vendor/chart.js" />
/// <reference path="vendor/jquery.js" />

function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

const colors = [
    "#83724e",
    "#d4aa5c",
    "#28a75c",
    "#5773dc",
    "#5c9dbe",
    "#8440ed",
    "#e67157",
    "#19e399",
    "#d231e0",
    "#e0315a",
    "#42bdff",
    "#45e342",
    "#b0e342",
    "#e69743"
]

function getColors(n) {
    return colors.slice(0, n)
}

function createPieChart(ctx, labels, data) {
    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: getColors(data.length)
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                labels: {
                    fontColor: "#fff"
                }
            }
        }
    });
}

function createBarChart(ctx, labels, datas, show_legend) {
    var datasets = []

    for (let i = 0; i < datas.length; i++) {
        const element = datas[i];

        if (typeof (element[0]) === "number") {
            datasets.push({
                data: element,
                backgroundColor: getColors(6),
            })
        } else {
            datasets.push({
                label: element[0],
                data: element[1],
                backgroundColor: getColors(6),
            })

        }
    }
    console.log(datasets)

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            scales: {
                xAxes: [{
                    ticks: {
                        fontColor: "#fff"
                    }
                }]
            },
            legend: {
                display: show_legend,
            },
            elements: {
                rectangle: {
                    borderColor: "#fff",
                    borderWidth: 1
                }
            }
        }
    });
}

function createLineChart(ctx, labels, data) {
    new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                backgroundColor: "#8b5dc2",
                borderColor: "#8b5dc2",
                data: data,
                fill: false,
                lineTension: 0,
            }]
        },
        options: {
            responsive: true,
            legend: {
                display: false,
            },
            tooltips: {
                mode: 'index',
                intersect: false,
            },
            hover: {
                mode: 'nearest',
                intersect: true
            },
            scales: {
                xAxes: [{
                    display: true,
                    scaleLabel: {
                        display: true,
                        labelString: 'Month/Year',
                        fontColor: "#fff"
                    },
                    ticks: {
                        fontColor: "#fff"
                    }
                }],
                yAxes: [{
                    display: true,
                    scaleLabel: {
                        display: true,
                        labelString: 'Nominations',
                        fontColor: "#fff"
                    },
                    ticks: {
                        fontColor: "#fff"
                    }
                }]
            }
        }
    })
}

$(function () {
    $('select.dropdown').dropdown()
    $("form").change(function () {
        $(this).submit()
    })
})