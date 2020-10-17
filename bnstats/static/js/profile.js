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

function generateColors(n) {
    return colors.slice(0, n)
}

function createPieChart(ctx, labels, data) {
    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: generateColors(data.length)
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

function createBarChart(ctx, data) {
    new Chart(ctx, {
        type: "bar",
        data: {
            labels: [
                "0:30 - 1:00",
                "1:01 - 2:00",
                "2:01 - 3:00",
                "3:01 - 4:00",
                "4:01 - 5:00",
                "above 5:00"
            ],
            datasets: [{
                data: data,
                backgroundColor: generateColors(6),
            }]
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
                display: false,
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