function drawMapData(selectedPark, data) {
    // parse json data for the selected park
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
    // console.log(park)

    // draw trails
    allLatLngs = []
    for ([trailType, trails] of Object.entries(park.getTrails())) {
        for (trail of trails) {
            trailLatLngs = trail.map(coords => L.latLng(coords.coords))
            allLatLngs = allLatLngs.concat(trailLatLngs)
            latLngAccuracies = trail.map(coords => coords.accuracy)
            drawTrail(trail, trailType)
        }
    }

    // draw pois
    pois = park.getPois()
    drawPois(pois)

    // fly to bounds
    allLatLngs = allLatLngs.concat(pois.map(poi => poi.coords))
    map.flyToBounds(allLatLngs, {duration: 0.5})
}

function drawTrail(trail, trailType) {
    trailLatLngs = trail.map(coords => L.latLng(coords.coords))
    latLngAccuracies = trail.map(coords => coords.accuracy)
    drawingProperties = trailTypeProperties[trailType]

    // for(i=0; i < coords.length; i++) {
    //     L.circle(coords[i], {
    //         opacity: 0,
    //         fillColor: drawingProperties.color,
    //         fillOpacity: 0.6,
    //         radius: latLngAccuracies[i]
    //     }).addTo(map);
    // }
    trail = L.polyline(trailLatLngs, {
        opacity: 1,
        color: drawingProperties.color,
        weight: drawingProperties.weight,
        smoothFactor: 2
    }).addTo(map);

    mapControl.addTrail(trail, trailType)
}

function drawPois(pois) {
    for(poi of pois) {
        // color = "blue"
        // L.circle(poi.coords, {
        //     opacity: 0,
        //     color: color,
        //     fillColor: color,
        //     fillOpacity: 0.4,
        //     radius: poi.accuracy
        // }).addTo(map);
        
        imgSize=80
        markerHtml = `<img src="https://drive.google.com/uc?id=${poi.imgId}" style="
            border-radius: 50%;
            border: 1px solid rgba(0, 0, 0, 0.75);
            max-width: ${imgSize}px !important;
            max-height: ${imgSize}px !important;
            object-fit: contain;
            margin-top:-${imgSize/2}px;
            margin-left:-${imgSize/2}px;"/>`
        poiMarker = new L.Marker(poi.coords, {
            icon: L.divIcon({
                html: markerHtml,
                iconSize: [0, 0]
            }),
            opacity: 0.75
        })
        
        popupImgSize = 300
        poiMarker.bindPopup(`
            <img src="https://drive.google.com/uc?id=${poi.imgId}" style="
                max-width: ${popupImgSize}px !important;
                max-height: ${popupImgSize}px !important;
                object-fit: contain;
                padding-bottom: 10px;"
            />
            <h4 style="
                text-align: center;
                font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif;">
                ${poi.description}
            </h4>
            `,
        {
            maxWidth: 400
        })

        poiMarker.addTo(map)
        mapControl.addPoi(poiMarker)
        // new L.Marker(poi.coords).addTo(map)
    }
}
debug("ready")
ready()