function drawMapData(data) {
    data.shift()
    coords = []
    coordsAccuracies = []
    pois = []
    poiAccuracies = []
    i = 2
    while(i < data.length) {
        line = String(data[i])
        if(line.includes("COORDS")) {
            coord = line.split(' ')[1].split(',')
            coord = [parseFloat(coord[0]), parseFloat(coord[1])]
            coords.push(L.latLng(coord[0], coord[1]))
        }
        else if(line.includes("ACCURACY")) {
            coordsAccuracies.push(parseFloat(line.split(' ')[1]))
        }
        else if(line.includes("POI")) {
            i+=2
            line = String(data[i])
            coord = line.split(' ')[1].split(',')
            coord = [parseFloat(coord[0]), parseFloat(coord[1])]
            pois.push(L.latLng(coord[0], coord[1]))
            i++
            line = String(data[i])
            poiAccuracies.push(parseFloat(line.split(' ')[1]))
            i++
        }
        else if(line.includes("START") || i+1 == data.length) {
            drawTrail(coords, coordsAccuracies)
            drawPOIs(pois, poiAccuracies)
            bounds = L.latLngBounds(coords)
            map.flyToBounds(bounds, {duration: 1});
            break // delete later
            coords = []
            coordsAccuracies = []
        }
        i++
    }
}

function drawTrail(coords, coordsAccuracies) {
    for(i=0; i < coords.length; i++) {
        color = "brown"
        L.circle(coords[i], {
            opacity: 0,
            fillColor: color,
            fillOpacity: 0.4,
            radius: coordsAccuracies[i]
        }).addTo(map);
    }
    L.polyline(coords, {color: 'brown'}).addTo(map);
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