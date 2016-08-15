//Creates a word cloud for a given document

var cloudLayoutWidth = 500
var cloudLayoutHeight = 300
var fill = d3.schemeCategory20

function makeWordCloud(elemId, docTokens) {
  var frequency_list = [{'text': 'study', 'freq': 20}, {'text': 'word', 'freq': 20},
                        {'text': 'another', 'freq': 10}, {'text': 'some', 'freq': 10}] 

  var layout = d3.layout.cloud()
      .size([cloudLayoutWidth, cloudLayoutHeight])
      .words(frequency_list)
      .fontSize(function(d) { return d.freq * 2 })
      .padding(5)
      .rotate(function() { return (~~(Math.random()*6) - 3) * 30 })
      .font('Impact')
      .on('end', function() { draw(frequency_list, elemId, layout) })

  layout.start()
}
  
function draw(words, elemId, layout) {
    d3.select('#'+elemId).append('svg')
            .attr('width', layout.size()[0])
            .attr('height', layout.size()[1])
            .attr('class', 'wordCloud')
          .append('g')
            //without the transform, words would get cutoff to the left and
            //  top, they would appear outside of the SVG area
            .attr('transform', 'translate(' + layout.size()[0] / 2 + ',' +
                               layout.size()[1] / 2 + ')')
          .selectAll('text')
            .data(words)
          .enter().append('text')
            .style('font-size', function(d) { return d.size + 'px'; })
            .style('font-family', 'Impact')
            .style('fill', function(d, i) { return fill[i]; })
            .attr('text-anchor', 'middle')
            .attr('transform', function(d) {
                return 'translate(' + [d.x, d.y] + ')rotate(' + d.rotate + ')';
            })
            .text(function(d) { return d.text; });
}

