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
    for (var [trailType, trails] of Object.entries(park.getTrails())) {
        for (trail of trails) {
            trailLatLngs = trail.map(coords => L.latLng(coords.coords))
            allLatLngs = allLatLngs.concat(trailLatLngs)
            drawTrail(trail, trailType)
        }
    }

    // draw pois
    pois = park.getPois()
    drawPois(pois)

    // fly to bounds
    allLatLngs = allLatLngs.concat(pois.map(poi => poi.coords))
    map.flyToBounds(allLatLngs, {duration: 2.5})
}

function drawTrail(trail, trailType) {
    trailLatLngs = trail.map(coords => L.latLng(coords.coords))
    latLngAccuracies = trail.map(coords => coords.accuracy)
    timeIds = trail.map(coords => coords.time)
    drawingProps = drawingProperties[trailType]

    if (mapControl.editMode) {
        for(i=0; i < trailLatLngs.length; i++) {
            L.circle(trailLatLngs[i], {
                radius: latLngAccuracies[i],
                fillColor: drawingProps.color,
                fillOpacity: 0.3,
                opacity: 0
            }).addTo(map)
            coordMarker = L.marker(trailLatLngs[i], {
                opacity: 0.6,
                draggable: true
            })
            coordMarker.bindPopup(timeIds[i])
            coordMarker.on('dragend', (e) => {
                time = e.target.getPopup().getContent()
                coords = e.target.getLatLng()
                coords = `${coords.lat},${coords.lng}`
                modification = {
                    type: "moveCoords",
                    id: time,
                    coords
                }
                mapControl.addModification(modification)
            })
            coordMarker.addTo(map)
        }
    }
    
    trail = L.polyline(trailLatLngs, {
        opacity: 1,
        color: drawingProps.color,
        weight: drawingProps.weight,
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
        
        imgSize=55
        markerHtml = `<img src="https://drive.google.com/uc?id=${poi.imgId}" style="
            border-radius: 50%;
            border: 1px solid rgba(0, 0, 0, 0.75);
            max-width: ${imgSize}px !important;
            max-height: ${imgSize}px !important;
            object-fit: contain;
            margin-top:-${imgSize/2}px;
            margin-left:-${imgSize/2}px;"/>`
        poiMarker = new L.marker(poi.coords, {
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

ready()