//This class holds the doc number, text and labels. It also builds
//  document-related structures (like a paragraph, list entry or dot)

function Document(number, text, title, labelX, labelY, topics) {
  this.number = number //Document number, as given by the server
  this.id = 'doc' + number //ID of this document in the DOM
  this.text = text //Text of the document
  var tempVocabText = {} //Used to build vocabText
  this.textList = text.replace(/[,.!?]/g, ' ').split(' ')
  //Pull out any extra spaces that were turned into words.
  for (var word = 0; word < this.textList.length; word++) {
    if (this.textList[word] == '' || this.textList[word] == ' ') {
      this.textList.splice(word, 1)
      //Decrement the index, since we want to check what's now at this index
      word--
    }
  }
  //Only store vocabulary words in vocabText
  for (var i = 0; i < this.textList.length; i++) {
    if (tempVocabText[this.textList[i]]) {
      tempVocabText[this.textList[i]] += 1
    }
    else if (map.vocab.indexOf(this.textList[i]) !== -1) {
      tempVocabText[this.textList[i]] = 1
    }
  }
  this.vocabText = [] //Text of the document that is in the vocabulary
  for (var word in tempVocabText) {
    this.vocabText.push({'text': word, 'freq': tempVocabText[word]})
  }
  this.title = title //Title of the document, not always the most informative
  this.labelX = labelX //Label of the document for the horizontal axis
  this.labelY = labelY //Label of the document for the vertical axis
  this.topics = topics //This becomes the topics when we have them
  this.changed = true //Has this document info changed?
}

Document.prototype = {
  constructor: Document,

  //Creates a <p> element to stick in the DOM
  toParagraph: function toParagraph() {
    if (!this.changed) { return }
    //This measures how far into the document's text we can slice
    var end = Math.min(this.text.length, 97)
    //Return a newly created paragraph
    this.changed = false
    return $('<p>').attr('id', this.id + 'listed')
                   .attr('class', 'listedDoc')
                   .text(this.text.slice(0, end) + '...')
  },

  //Creates a list entry <div> to stick in the DOM and a corresponding modal
  toListEntry: function toListEntry() {
    //This measures how far into the document's text we can slice
    var end = Math.min(this.text.length, 97)
    var titleString = 'title: ' + this.title
    var textString = 'text: ' + this.text.slice(0, end) + '...'
    var modalId = 'modal' + this.id
    //Create the button that lets you get to the document's modal
    var modalButton = $('<button>').attr('id', this.id + 'listedButton')
                                   .attr('class', 'listedButton btn btn-sm')
                                   .attr('data-toggle', 'modal')
                                   .attr('data-target', '#' + modalId)
                                   .text('Select Document')
    if (this.changed) {
      //Create the modal itself
      var tab1Id = 'modal' + this.id + 'Tab1'
      var tab2Id = 'modal' + this.id + 'Tab2'
      var tab3Id = 'modal' + this.id + 'Tab3'
      var temp = $('<div>')
      //Basically what I do is create a very long template, append it to temp
      //  to get it parsed, then pull it out of temp and put it in the modals div
      //I'm not sure whether this is better or worse than building it using
      //  JQuery and .attr() below.
      var tmpMod = '<div id="' + modalId + '" class="modal fade" ' +
                     'role="dialog">' + 
                     '<div class="modal-dialog">' + 
                       '<div class="modal-content">' +
                         '<div class="modal-header">' +
                           '<h4 class="modal-header">' +
                             'Title: ' + this.title +
                           '</h4>' +
                         '</div>' +
                         '<div class="modal-body">' +
                           '<ul class="nav nav-tabs">' + 
                             '<li class="active">' +
                               '<a data-toggle="tab" href="#' + tab1Id + '">' +
                                 'Main' +
                               '</a>' +
                             '</li>' +
                             '<li>' +
                               '<a data-toggle="tab" href="#' + tab2Id + '">' +
                                 'Text' +
                               '</a>' +
                             '</li>' +
                             '<li>' +
                               '<a data-toggle="tab" href="#' + tab3Id + '">' +
                                 'Topics' +
                               '</a>' +
                             '</li>' +
                           '</ul>' +
                           '<div class="tab-content">' +
                             '<div id="' + tab1Id + '" class="tab-pane fade ' +
                               'active in">' +
                               '<h4 class="modalSubheader">Metadata and Metrics</h4>' +
                               '<div id="' + tab1Id + 'Meta"></div>' +
                               '<h4 class="modalSubheader">Word Cloud</h4>' +
                               '<div id="' + tab1Id + 'Cloud"></div>' +
                             '</div>' +
                             '<div id="' + tab2Id + '" class="tab-pane fade docTextTab">' +
                               '<p>' + this.text + '</p>' +
                             '</div>' +
                             '<div id="' + tab3Id + '" class="tab-pane fade">' +
                             '</div>' +
                           '</div>' +
                         '</div>' +
                       '</div>' +
                     '</div>' +
                   '</div>'
      temp.html(tmpMod)
      var modal = temp.first()
      //Stick the modal and tabs in the DOM
      $("#modals").append(modal)
      if (this.topics !== null) {
        var data = []
        for (var i = 0; i < this.topics.length; i++) {
          var topic = Number(this.topics[i])
          if (topic > 0) {
            data.push({name: 'Topic ' + i, value: topic})
          }
        }
        makePieChart(tab3Id, data)
        makeTopicLists(tab3Id, this.topics, map.topicTokens)
      }
      else {
        $("#"+tab3Id).append("<p>No topics yet, please label more documents!</p>")
      }
      makeWordCloud(tab1Id + 'Cloud', this.vocabText)
      generateMetrics(tab1Id + 'Meta', this.text, this.textList)
      //Return a newly created list entry
      this.changed = false
    }
    return $('<div>').attr('id', this.id + 'listed')
                   .attr('class', 'listedDoc')
                   .html(titleString + '<br>' + textString + '<br>')
                   .append(modalButton)
  },

  //Creates a Dot object from this document
  toDot: function toDot() {
    return new Dot(this.number, this.labelX * 100, this.labelY * 100)
  }
}

function makeTopicLists(elemId, topics, topicTokens) {
  $('#'+elemId+' p').remove()
  for (var i = 0; i < topics.length; i++) {
    var topic = Number(topics[i])
    if (topic > 0) {
      var topicsList = topicTokens[i]
      $("#"+elemId).append('<p class="topicsList">Topic ' + i + ', ' +
                           parseFloat(topic*100).toFixed(0) + '%: ' +
                           topicsList.join(', ') + '</p>')
    }
  }
}

function generateMetrics(elemId, text, textList) {
  var tokenCount = textList.length
  var typeCount = $.uniqueSort(textList.slice()).length
  var lengthInChars = text.length
  var metrics = '<p><strong>Token Count:</strong> ' + tokenCount + '</p>' +
                '<p><strong>Length in Characters:</strong> ' + lengthInChars + '</p>' +
                '<p><strong>Type Count:</strong> ' + typeCount + '</p>'
  $('#'+elemId+' p').remove()
  $('#'+elemId).append(metrics)
}
