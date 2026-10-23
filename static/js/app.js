(function () {
    "use strict";

    function initConfirmations() {
        var forms = document.querySelectorAll("form[data-confirm]");
        forms.forEach(function (form) {
            form.addEventListener("submit", function (event) {
                var message = form.getAttribute("data-confirm") || "Are you sure?";
                if (!window.confirm(message)) {
                    event.preventDefault();
                }
            });
        });
    }

    function formatAxisValue(value) {
        var number = Number(value);
        if (!isFinite(number)) {
            return value;
        }
        return number.toLocaleString(undefined, {
            maximumFractionDigits: 2
        });
    }

    function initCharts() {
        var dataElement = document.getElementById("dashboard-charts");
        if (!dataElement || typeof window.Chart === "undefined") {
            return;
        }

        var payload;
        try {
            payload = JSON.parse(dataElement.getAttribute("data-charts"));
        } catch (error) {
            return;
        }

        if (!payload || !payload.has_data) {
            return;
        }

        window.Chart.defaults.font.family =
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
        window.Chart.defaults.color = "#5b6470";
        window.Chart.defaults.font.size = 12;

        var trendCanvas = document.getElementById("trendChart");
        if (trendCanvas && payload.trend) {
            new window.Chart(trendCanvas, {
                type: "bar",
                data: {
                    labels: payload.trend.labels,
                    datasets: [
                        {
                            label: "Credits",
                            data: payload.trend.credits,
                            backgroundColor: "#2f6f94",
                            borderRadius: 2
                        },
                        {
                            label: "Debits",
                            data: payload.trend.debits,
                            backgroundColor: "#b42318",
                            borderRadius: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                boxWidth: 10,
                                boxHeight: 10,
                                padding: 16
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return context.dataset.label + ": " + formatAxisValue(context.parsed.y);
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: formatAxisValue
                            },
                            grid: {
                                color: "#e5e8eb"
                            }
                        }
                    }
                }
            });
        }

        var categoryCanvas = document.getElementById("categoryChart");
        if (categoryCanvas && payload.categories && payload.categories.labels.length) {
            new window.Chart(categoryCanvas, {
                type: "bar",
                data: {
                    labels: payload.categories.labels,
                    datasets: [
                        {
                            label: "Debit spending",
                            data: payload.categories.totals,
                            backgroundColor: "#2f6f94",
                            borderRadius: 2
                        }
                    ]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return formatAxisValue(context.parsed.x);
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: {
                                callback: formatAxisValue
                            },
                            grid: {
                                color: "#e5e8eb"
                            }
                        },
                        y: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        initConfirmations();
        initCharts();
    });
})();
