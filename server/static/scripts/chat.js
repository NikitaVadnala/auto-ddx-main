// Collapsible
const coll = document.getElementsByClassName("collapsible")

for (let i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function () {
    this.classList.toggle("active")
    const content = this.nextElementSibling
    if (content.style.maxHeight) content.style.maxHeight = null
    else content.style.maxHeight = content.scrollHeight + "px"
  })
}

// Gets the first message
;(function firstBotMessage() {
  // TODO: Update Message
  let firstMessage =
    "Hi. please tell us your symptoms, we are here to diagnose your disease?"
  document.getElementById("botStarterMessage").innerHTML =
    '<p class="botText"><span>' + firstMessage + "</span></p>"
  let time = (function getTime() {
    let today = new Date()
    hours = today.getHours()
    minutes = today.getMinutes()
    if (hours < 10) hours = "0" + hours
    if (minutes < 10) minutes = "0" + minutes
    let time = hours + ":" + minutes
    return time
  })()
  document.querySelector("#chat-timestamp").innerHTML += time
  document.getElementById("userInput").scrollIntoView(false)
})()

// Retrieves the response
function getHardResponse(userText) {
  let botResponse = getBotResponse(userText)
  let botHtml = '<p class="botText"><span>' + botResponse + "</span></p>"
  document.querySelector("#chatbox").innerHTML += botHtml
  const el = document.querySelectorAll(".botText")
  el[el.length - 1].scrollIntoView({ behavior: "smooth" })
}

function reponse(botText, body) {
  const rand = Math.random().toString()
  switch (body.type) {
    case "scaler":
      botText.innerHTML = `<span>${body.payload}</span>`
      break
    case "dropdown":
      // TODO: implement dropdown response
      throw "Not Implemented"
      break
    case "attachment":
      botText.innerHTML = `
          <span>
            ${body.payload}<br/>
            <form method="post" enctype="multipart/form-data" id="${rand}">
              <span style="font-size: small; color: red;" id="${rand}-err"></span>
              <input type="file" name="file" id="${rand}-file" style="display: none;">
              <label for="${rand}-file"><i class="fa fa-paperclip" aria-hidden="true"></i></label>
              <input type="submit" value="Upload">
            </form>
          </span>
          `
      document.getElementById(`${rand}`).addEventListener("submit", (e) => {
        e.preventDefault()
        const file = document.getElementById(`${rand}-file`)
        if (file.files.length < 1 || file.files[0].size > Math.pow(2, 20) * 5) {
          document.getElementById(`${rand}-err`).innerHTML =
            "Please select a file or Select file less than 5MB size"
          return
        }
        const payload = new FormData()
        payload.append("type", "attachment")
        payload.append("payload", file.files[0])
        e.target.parentElement.innerHTML = `...`
        fetch("/api/chatbot", {
          method: "post",
          mode: "same-origin",
          headers: {
            Accept: "application/json",
          },
          body: payload,
        })
          .then((data) => data.json())
          .then((body) => {
            e.target.innerHTML = `${file.files[0].name}`
            reponse(botText, body)
          })
          .catch((_) => {
            e.target.innerHTML = `unable to send ${file.files[0].name}, try again later`
          })
      })
      break
    default:
      botText.innerHTML = `<span>Invalid Response from Server</span>`
  }
}

//Gets the text text from the input box and processes it
function responder() {
  const chatbox = document.getElementById("chatbox")
  // update user response
  let userText = document.querySelector("#textInput").value.trim()
  if (userText == "") return
  let userHtml = '<p class="userText"><span>' + userText + "</span></p>"
  document.querySelector("#textInput").value = ""
  chatbox.innerHTML += userHtml
  let el = document.querySelectorAll(".userText")
  el[el.length - 1].scrollIntoView({ behavior: "smooth" })
  // update bot response
  let [type, payload] = ["", ""]
  const botText = document.createElement("p")
  botText.setAttribute("class", "botText")
  botText.innerHTML = `<span>...</span>`
  chatbox.appendChild(botText)
  type = "scaler"
  payload = userText
  fetch("/api/chatbot", {
    method: "post",
    mode: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      type,
      payload,
    }),
  })
    .then((res) => res.json())
    .then((body) => {
      reponse(botText, body)
    })
    .catch((_err) => {
      botText.innerHTML = `<span>unable to reach, try again later</span>`
    })
  el = document.querySelectorAll(".botText")
  el[el.length - 1].scrollIntoView({ behavior: "smooth" })
}

document.querySelector("#textInput").addEventListener("keypress", function (e) {
  if (e.which == 13) {
    responder()
  }
})
