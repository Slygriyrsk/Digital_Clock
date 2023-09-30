// This code contains the change of both date, time and day.

function updateClock() {
  const now = new Date();
  const hourElement = document.getElementById("hour");
  const minuteElement = document.getElementById("minute");
  const secondElement = document.getElementById("second");
  const dayElement = document.getElementById("day");
  const dateElement = document.getElementById("date");
  const yearElement = document.getElementById("year");

  const hours = now.getHours().toString().padStart(2, "0");
  const minutes = now.getMinutes().toString().padStart(2, "0");
  const seconds = now.getSeconds().toString().padStart(2, "0");
  const daysOfWeek = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday"
  ];
  const day = daysOfWeek[now.getDay()];

  const dayOfMonth = now.getDate().toString().padStart(2, "0");
  const month = (now.getMonth() + 1).toString().padStart(2, "0");
  const year = now.getFullYear();

  const ampm = now.getHours() >= 12 ? "PM" : "AM";

  hourElement.textContent = hours;
  minuteElement.textContent = minutes;
  secondElement.textContent = seconds;
  dayElement.textContent = day;
  dateElement.textContent = `${dayOfMonth}/${month}/${year}`;
  yearElement.textContent = ampm;
}

// Update the clock every second
setInterval(updateClock, 1000);

// Initial call to set the clock
updateClock();

// This code just contains the change of time
/* let hrs = document.getElementById("hour");
  let min = document.getElementById("minute");
  let sec = document.getElementById("second");

setInterval(()=> {
  let currentTime = new Date();
  hrs.innerHTML = currentTime.getHours();
  min.innerHTML = currentTime.getMinutes();
  sec.innerHTML = currentTime.getSeconds();
}, 1000); */
