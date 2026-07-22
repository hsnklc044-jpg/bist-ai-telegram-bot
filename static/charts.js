document.addEventListener("DOMContentLoaded", () => {

    Chart.defaults.font.family = "Segoe UI";
    Chart.defaults.color = "#cfe8ff";
    Chart.defaults.animation.duration = 1200;

    console.log("QuantBIST Charts Loaded");


    // Portfolio Allocation Chart

    const portfolioChart = document.getElementById(
        "portfolioChart"
    );


    if (portfolioChart) {

        new Chart(portfolioChart, {

            type: "doughnut",

            data: {

                labels: [
                    "EREGL",
                    "BIMAS",
                    "Cash"
                ],

                datasets: [{

                    data: [
                        40,
                        40,
                        20
                    ]

                }]

            },

            options: {

                responsive:true,

                plugins:{
                    legend:{
                        position:"bottom"
                    }
                }

            }

        });

    }



    // Equity Curve Chart

    const equityChart = document.getElementById(
        "equityChart"
    );


    if (equityChart) {


        new Chart(equityChart, {


            type:"line",


            data:{


                labels:[
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May"
                ],


                datasets:[{


                    label:"Portfolio Value",


                    data:[
                        100000,
                        102500,
                        101800,
                        106000,
                        109284
                    ],


                    tension:0.4


                }]


            },


            options:{


                responsive:true,


plugins:{
    legend:{
        position:"bottom",
        labels:{
            color:"#cfe8ff",
            font:{
                size:12,
                weight:"bold"
            }
        }
    },

    tooltip:{
        enabled:true,
        backgroundColor:"#101827",
        titleColor:"#4fdcff",
        bodyColor:"#ffffff",
        borderColor:"#38bdf8",
        borderWidth:1
    }
}


            }


        });


    }


});

function updateClock(){

const now=new Date();


document.getElementById("clock").innerHTML =
now.toLocaleTimeString("tr-TR");

}


setInterval(updateClock,1000);

updateClock();