function drawMapData(park, data) {
    currPark = null
    parkData = []
    for (obj of data) {
        if (obj.header === "START") {
            currPark = obj.park
        }
        else if (currPark === park) {
            parkData.push(obj)
        }
    }
    console.log(parkData)
    coords = parkData.filter(obj => {
        if (obj.header === "COORDS") return true
        return false
    })
    coordlatLngs = coords.map(e => e.coords)
    coordAccuracies = coords.map(e => accuracy)
    pois = parkData.filter(obj => {
        if (obj.header === "POI") return true
        return false
    })
    poiLatLngs = pois.map(e => e.coords)
    poiAccuracies = pois.map(e => accuracy)
    drawTrail(coordlatLngs, coordAccuracies)
    drawPOIs(poiLatLngs, poiAccuracies)
    bounds = L.latLngBounds(coordlatLngs)
    map.flyToBounds(bounds, {duration: 2});
}

function drawTrail(coords, coordsAccuracies) {
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
        color: 'brown',
        smoothFactor: 2,
        opacity: 0.7,
        weight: 7
    }).addTo(map);
}

function drawPOIs(pois, poiAccuracies) {
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