function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

function generateColors(n) {
    data = []
    for (var i = 0; i < n; i++) {
        data.push(getRandomColor())
    }
    return data
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
            labels: ["<= 1 minute", "<= 2 minutes", "<= 3 minutes", "<= 4 minutes", "<= 5 minutes", "> 5 minutes"],
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