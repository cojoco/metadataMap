//This should create a pie chart to stick in the modal

function makePieChart(elemId, data) {

  $("#"+elemId+' svg').remove()

  var width = 400
  var height = 400
  var radius = Math.min(width, height) / 2

  var color = d3.scaleOrdinal()
                .range(["#98abc5", "#8a89a6", "#7b6888", "#6b486b",
                        "#a05d56", "#d0743c", "#ff8c00"])
 
  var arc = d3.arc()
              .outerRadius(radius - 10)
              .innerRadius(0)

  var labelArc = d3.arc()
                   .outerRadius(radius - 40)
                   .innerRadius(radius - 40)

  var pie = d3.pie()
              .sort(null)
              .value(function(d) { return d.value })

  var svg = d3.select('#' + elemId).append('svg')
              .attr('width', width)
              .attr('height', height)
              .append('g')
              .attr('transform', 'translate(' + width / 2 + ',' +
                    height / 2 + ')')


  var g = svg.selectAll('.arc')
            .data(pie(data))
            .enter().append('g')
            .attr('class', 'arc')

  g.append('path')
    .attr('d', arc)
    .style('fill', function(d) { return color(d.data.name) })

  g.append('text')
    .attr('text-anchor', 'middle')
    .attr('transform', function(d) {
      return 'translate(' + (0.8*labelArc.centroid(d)[0]) + ',' + (0.8*labelArc.centroid(d)[1]) + ')'
    })
    .attr('dy', '.35em')
    .text(function(d) { return d.data.name })

  function type(d) {
    d.value = +d.value
    return d
  }
}
