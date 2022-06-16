function drawMapData(selectedPark, data) {
    park = new Park()
    currPark = null
    currTrailType = null
    currTrail = null
    for (obj of data) {
        if (obj.header === "START") {
            if (currPark === selectedPark && currTrail != null) {
                park.addTrail(currTrail, currTrailType)
            }
            currPark = obj.park
            currTrailType = obj.trailType
            currTrail = []
        }
        else if (obj.header === "POI") {
            if (obj.park === selectedPark) {
                park.addPoi(obj)
            }
        }
        else if (obj.header === "COORDS") {
            if (currPark === selectedPark) {// "COORDS"
                currTrail.push(obj)
            }
        }
        else {
            throw "something went wrong while parsing data for the selected park"
        }
    }
    park.addTrail(currTrail, currTrailType)
    console.log(park)

    allLatLngs = []
    for ([trailType, trails] of Object.entries(park.getTrails())) {
        drawingProperties = trailTypeProperties[trailType]
        for (trail of trails) {
            trailLatLngs = trail.map(coords => L.latLng(coords.coords))
            allLatLngs = allLatLngs.concat(trailLatLngs)
            drawTrail(trailLatLngs, null, drawingProperties)
        }
    }

    pois = park.getPois().map(poi => poi.coords)
    poiAccuracies = park.getPois().map(poi => poi.accuracy)
    drawPois(pois, poiAccuracies)
    allLatLngs = allLatLngs.concat(pois)

    map.flyToBounds(allLatLngs, {duration: 0.5})



    // coords = parkData.filter(obj => {
    //     if (obj.header === "COORDS") return true
    //     return false
    // })
    // coordlatLngs = coords.map(e => e.coords)
    // coordAccuracies = coords.map(e => e.accuracy)
    // pois = parkData.filter(obj => {
    //     if (obj.header === "POI") return true
    //     return false
    // })
    // poiLatLngs = pois.map(e => e.coords)
    // poiAccuracies = pois.map(e => e.accuracy)
    // drawTrail(coordlatLngs, coordAccuracies)
    // drawPOIs(poiLatLngs, poiAccuracies)
    // bounds = L.latLngBounds(coordlatLngs.concat(poiLatLngs))
    // map.flyToBounds(bounds, {duration: 2});
}

function drawTrail(coords, coordsAccuracies, drawingProperties) {
    // for(i=0; i < coords.length; i++) {
    //     color = "brown"
    //     L.circle(coords[i], {
    //         opacity: 0,
    //         fillColor: color,
    //         fillOpacity: 0.4,
    //         radius: coordsAccuracies[i]
    //     }).addTo(map);
    // }
    L.polyline(coords, {
        opacity: 1,
        color: drawingProperties.color,
        weight: drawingProperties.weight,
        smoothFactor: 2
    }).addTo(map);
}

function drawPois(pois, poiAccuracies) {
    for(i in pois) {
        color = "blue"
        L.circle(pois[i], {
            opacity: 0,
            color: color,
            fillColor: color,
            fillOpacity: 0.4,
            radius: poiAccuracies[i]
        }).addTo(map);
        L.marker(pois[i]).addTo(map)
    }
}