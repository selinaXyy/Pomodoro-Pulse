let interval;

const workTime = 25 * 60;
const shortBreakTime = 5 * 60;
const longBreakTime = 15 * 60;

const body = document.body;
const timerPage = document.querySelector(".timerPage");
const note = document.getElementById("userNote");
const timerOuter = document.querySelector(".timerOuter");
const timerInner = document.querySelector(".timerInner");
const timerButton = document.querySelector(".timerBtn");
const resetButton = document.getElementById("resetBtn");

const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

document.addEventListener("DOMContentLoaded", ()=>{
    //add event listener
    resetButton.addEventListener("click", ()=>{
        if (confirm("Are you sure you want to quit this Pomodoro session?")){
            clearInterval(interval);
            window.location.href = 'https://www.pomodoro-pulse.com/pomodoro/timer';
        }
    });

    timerButton.addEventListener("click", ()=>{
        const sessions = [
            {duration: workTime, mode: "work"},
            {duration: shortBreakTime, mode: "shortBreak"},
            {duration: workTime, mode: "work"},
            {duration: shortBreakTime, mode: "shortBreak"},
            {duration: workTime, mode: "work"},
            {duration: shortBreakTime, mode: "shortBreak"},
            {duration: workTime, mode: "work"},
            {duration: longBreakTime, mode: "longBreak"}
        ];

        body.style.paddingTop = "5rem";
        timerPage.style.margin = "0 auto"; 
        note.style.display = "none";
        sideBar.style.display = "none";
        timerButton.style.display = "none";
        resetButton.style.display = "inline-block";
        //run the first session
        runSession(0, sessions);
    });
});

function runSession(indexPar, sessionsPar){
    if (indexPar < sessionsPar.length){
        var currentSession = sessionsPar[indexPar];

        if (currentSession.mode === "work"){
            workSound.play();
        }
        else{
            breakSound.play();
    
        }

        setTimeout(()=>{
            //change mode
            setSessionStyle(currentSession.mode);
            //set timer & call next recursive func
            setTimer(currentSession.duration, ()=>{
                runSession(indexPar + 1, sessionsPar)
            });
            }, 3000);
    }
    else{
        //if all sessions are finished
        finishSound.play();
        setTimeout(()=>{
            congratsSound.play();
            showCongrats();
        }, 4000);
        setTimeout(() => {
            // call 'addSession' URL
            fetch("https://www.pomodoro-pulse.com/pomodoro/addSession", {
                method: 'POST',
                credentials: 'include',  // ensures cookies, such as session cookies, are included in the request. Important for authenticated sessions.
                headers: {
                    'X-CSRF-Token': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json()) // parses the JSON response returned from 'fetch' and converts it into a JavaScript object.
            .then(data => { // the JavaScript object derived from 'response.json()'
                if (data.status === "success") {
                    window.location.href = "https://www.pomodoro-pulse.com/pomodoro/timer";
                } else {
                    alert('We encountered an issue while recording your new session.\nPlease reach out to us via "Help & Feedback", and we will resolve it as soon as possible.');
                    console.error(data.message);
                }
            })
            .catch(error => {
                if (confirm('We encountered an issue while recording your new session.\nPlease reach out to us via "Help & Feedback", and we will resolve it as soon as possible.')){
                    console.error('There was a problem with the fetch operation:', error);
                    window.location.href = 'https://www.pomodoro-pulse.com/pomodoro/timer';
                }

            });

        }, 10000); 
    }
}

function setSessionStyle(modePar){
    body.className = modePar;
    timerOuter.className = "timerOuter " + modePar;
    timerInner.className = "timerInner " + modePar;
}

function setTimer(secondsPar, callback){
    let secondsRemaining = secondsPar;

    //clear any existing interval first to ensure no overlaps
    clearInterval(interval);
    interval = setInterval(()=>{
        displayTime(secondsRemaining);

        if (secondsRemaining <= 0){
            clearInterval(interval);
            callback();
        }
        else{
            secondsRemaining--;
        }
    }, 1000);
}

function displayTime(secondsRemainingPar){
    //calculate time
    let minutes = Math.floor(secondsRemainingPar / 60);
    let seconds = secondsRemainingPar % 60;
    let timeToDisplay;
    if (minutes === 0){
        timeToDisplay = `00:${seconds < 10 ? 0 : ""}${seconds}`;
    }
    else{
        timeToDisplay = `${minutes < 10 ? 0 : ""}${minutes}:${seconds < 10 ? 0 : ""}${seconds}`;
    }

    //display time
    timerInner.textContent = timeToDisplay;
}

//congrats effect
function showCongrats(){
    const duration = 1000 * 3, //5 sec
	animationEnd = Date.now() + duration,
	defaults = { startVelocity: 30, spread: 360, ticks: 20, zIndex: 0 };

    const congratsInterval = setInterval(function () {
        const timeLeft = animationEnd - Date.now();

        if (timeLeft <= 0) {
            return clearInterval(congratsInterval);
        }

        const particleCount = 200 * (timeLeft / duration);

        // since particles fall down, start a bit higher than random
        confetti(
            Object.assign({}, defaults, {
                particleCount,
                origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 }
            })
        );
        confetti(
            Object.assign({}, defaults, {
                particleCount,
                origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 }
            })
        );
    }, 250);
}

function randomInRange(min, max) {
	return Math.random() * (max - min) + min;
}
