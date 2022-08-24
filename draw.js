function drawParkData(data) {
    // parse json data for the selected park
    park = new Park()
    currTrailType = null
    currTrail = null
    for (obj of data) {
        switch (obj.header) {
            case "START":
                if (currTrail != null) {
                    park.addTrail(currTrail, currTrailType)
                }
                currTrailType = obj.trailType
                currTrail = []
                break;
        
            case "COORDS":
                currTrail.push(obj)
                break;
        
            case "POI":
                park.addPoi(obj)
                break;
        
            case "INFO":
                park.addInfoMarker(obj)
                break;
        
            case "INTERSECTION":
                park.addIntersection(obj)
                break;
        
            default:
                throw "Something went wrong while parsing data for the selected park"
        }
    }
    park.addTrail(currTrail, currTrailType)
    // console.log(park)

    // draw trails
    allLatLngs = []
    for (var [trailType, trails] of Object.entries(park.getTrails())) {
        for (trail of trails) {
            if (trail !== null) {
                trailLatLngs = trail.map(coords => L.latLng(coords.coords))
                allLatLngs = allLatLngs.concat(trailLatLngs)
                drawTrail(trail, trailType)
            }
        }
    }

    // draw pois
    drawPois(park.pois)

    // draw info markers
    drawInfoMarkers(park.infoMarkers)

    // draw intersections
    drawIntersections(park.intersections)

    // fly to bounds
    allLatLngs = allLatLngs.concat(park.pois.map(poi => poi.coords))
    allLatLngs = allLatLngs.concat(park.infoMarkers.map(info => info.coords))
    allLatLngs = allLatLngs.concat(park.intersections.map(intersection => intersection.coords))
    map.flyToBounds(allLatLngs, {duration: (mapControl.editMode) ? 0.01 : 2.5})
}

function drawTrail(trail, trailType) {
    trailLatLngs = trail.map(coords => L.latLng(coords.coords))
    latLngAccuracies = trail.map(coords => coords.accuracy)
    timeIds = trail.map(coords => coords.time)
    
    drawingProps = null
    if (trailType in mapControl.drawingProperties.trail) {
        drawingProps = mapControl.drawingProperties.trail[trailType]
    } else {
        drawingProps = mapControl.drawingProperties.trail["undefined"]
        console.log(`Need to define drawing properties for trail type ${trailType}`)
    }

    if (mapControl.editMode) {
        for(i=0; i < trailLatLngs.length; i++) {
            accuracy = L.circle(trailLatLngs[i], {
                radius: latLngAccuracies[i],
                fillColor: drawingProps.color,
                fillOpacity: mapControl.drawingProperties.opacity.coords.accuracy,
                opacity: 0
            }).addTo(map)
            mapControl.addTrail(accuracy, trailType)

            coordMarker = L.marker(trailLatLngs[i], {
                opacity: mapControl.drawingProperties.opacity.coords.marker,
                draggable: true
            })
            const time = timeIds[i]
            function createModificationHTML(action, description, modification) {
                return `
                    <p>${description}</p>
                    <button
                        onclick='mapControl.addModification({
                            type: "${modification}",
                            id: "${time}"
                        })'>
                        ${action}
                    </button>
                `
            }
            const rand = Math.random()
            coordMarker.bindPopup(`
                <p>${timeIds[i]}</p>
                ${createModificationHTML('Delete', 'Delete this coordinate', 'deleteCoords')}
                ${createModificationHTML('Delete', 'Delete this trail', 'deleteTrail')}
                ${createModificationHTML('Split', 'Delete this coordinate and separate trail into two', 'splitTrail')}
                <p>Change Trail Type</p>
                <input type="text" id="${rand}">
                <button
                    onclick='mapControl.addModification({
                        type: "changeTrailType",
                        id: "${time}",
                        trailType: document.getElementById("${rand}").value
                    })'>
                    Submit
                </button>
            `)
            coordMarker.on('dragend', (e) => {
                newCoords = e.target.getLatLng()
                newCoords = `${newCoords.lat},${newCoords.lng}`
                mapControl.addModification({
                    type: "moveCoords",
                    id: time,
                    coords: newCoords
                })
            })
            coordMarker.addTo(map)
            mapControl.addTrail(coordMarker, trailType)
        }
    }
    
    trail = L.polyline(trailLatLngs, {
        opacity: mapControl.drawingProperties.opacity.trail,
        color: drawingProps.color,
        weight: drawingProps.weight,
        smoothFactor: 2
    }).addTo(map);

    mapControl.addTrail(trail, trailType)
}

function drawPois(pois) {
    for(poi of pois) {
        imgSize=55
        markerHtml = `<img src="https://drive.google.com/uc?id=${poi.imgId}" style="
            border-radius: 50%;
            border: 1px solid rgba(0, 0, 0, 0.75);
            max-width: ${imgSize}px !important;
            max-height: ${imgSize}px !important;
            object-fit: contain;
            margin-top:-${imgSize/2}px;
            margin-left:-${imgSize/2}px;"/>`
        const time = poi.time
        poiMarker = new L.marker(poi.coords, {
            icon: L.divIcon({
                html: markerHtml,
                iconSize: [0, 0]
            }),
            opacity: mapControl.drawingProperties.opacity.poi.img,
            draggable: mapControl.editMode
        })
        
        if (mapControl.editMode) {
            const rand1 = Math.random()
            const rand2 = Math.random()
            poiMarker.bindPopup(`
                <p>${time}</p>
                <p>Delete POI</p>
                <button
                    onclick='mapControl.addModification({
                        type: "deletePoi",
                        id: "${time}"
                    })'>
                    Delete
                </button>
                <p>Change Description</p>
                <input type="text" id="${rand1}" value="${poi.description}">
                <button
                    onclick='mapControl.addModification({
                        type: "changePoiDescription",
                        id: "${time}",
                        description: document.getElementById("${rand1}").value
                    })'>
                    Submit
                </button>
                <p>Change Google Drive Image ID</p>
                <input type="text" id="${rand2}">
                <button
                    onclick='mapControl.addModification({
                        type: "changePoiLink",
                        id: "${time}",
                        imgId: document.getElementById("${rand2}").value
                    })'>
                    Submit
                </button>
            `)
            poiMarker.on('dragend', (e) => {
                newCoords = e.target.getLatLng()
                newCoords = `${newCoords.lat},${newCoords.lng}`
                mapControl.addModification({
                    type: "movePoi",
                    id: time,
                    coords: newCoords
                })
            })
            
            color = "blue"
            accuracy = L.circle(poi.coords, {
                radius: poi.accuracy,
                fillColor: "#3333ff",
                fillOpacity: mapControl.drawingProperties.opacity.poi.accuracy,
                opacity: 0
            }).addTo(map);
            mapControl.addPoi(accuracy)
        }
        else {
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
        }

        poiMarker.addTo(map)
        mapControl.addPoi(poiMarker)
    }
}

function drawInfoMarkers(infoMarkers) {
    for (var info of infoMarkers) {
        iconUrl = "https://drive.google.com/uc?id="
        description = null
        switch (info.type) {
            case "Text":
                iconUrl += '1IbCnTtj6qICPM5lc3k-PCf7vKeuYv3q-'
                description = info.description
                break;
        
            case "Parking":
                iconUrl += '1pwj2xXKGuKKod-PRmGfw2fB3ANua-Vu4'
                description = "Parking"
                break;
        
            default:
                throw 'Invalid info marker type';
        }
        iconSize = 30
        iconAnchor = 15
        icon = L.icon({
            iconUrl,
            iconSize: [iconSize, iconSize],
            iconAnchor: [iconAnchor, iconAnchor]
        })
        infoMarker = L.marker(info.coords, {
            icon,
            draggable: mapControl.editMode
        })

        const time = info.time
        if (mapControl.editMode) {
            const rand = Math.random()
            infoMarker.bindPopup(`
                <p>${time}</p>
                <p>Delete Info Marker</p>
                <button
                    onclick='mapControl.addModification({
                        type: "deleteInfoMarker",
                        id: "${time}"
                    })'>
                    Delete
                </button>
                <p>Change Description</p>
                <input type="text" id="${rand}" value="${description}">
                <button
                    onclick='mapControl.addModification({
                        type: "changeInfoDescription",
                        id: "${time}",
                        description: document.getElementById("${rand}").value
                    })'>
                    Submit
                </button>
            `)
            infoMarker.on('dragend', (e) => {
                newCoords = e.target.getLatLng()
                newCoords = `${newCoords.lat},${newCoords.lng}`
                mapControl.addModification({
                    type: "moveInfoMarker",
                    id: time,
                    coords: newCoords
                })
            })
        } else {
            infoMarker.bindPopup(`
                <h4 style="
                    text-align: center;
                    font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif;">
                    ${description}
                </h4>
            `)
        }
        
        infoMarker.addTo(map);

        mapControl.addInfoMarker(infoMarker)
    }
}

function drawIntersections(intersections) {
    for (var intersection of intersections) {
        iconUrl = "https://drive.google.com/uc?id="
        switch (intersection.numPaths) {
            case "2":
                iconUrl += '1qJyQ-im5ffr-Dj-mtS_2uGYIAAB6PAtI'
                break;
        
            case "3":
                iconUrl += '1pdsj2qfeY0D0a8Awh9KwL6EmkwaaQyL5'
                break;
        
            case "4":
                iconUrl += '1RuDL8lgKqS2Qtj8W0CSIjVPM_W66h0hO'
                break;
        
            case "5":
                iconUrl += '1-pvCWlcugAn4ZNYVzjZ6vsb0Y6av6NEX'
                break;
        
            default:
                throw 'Invalid number for intersection paths';
        }
        iconSize = 30
        iconAnchor = 15
        icon = L.icon({
            iconUrl,
            iconSize: [iconSize, iconSize],
            iconAnchor: [iconAnchor, iconAnchor]
        })
        intersectionMarker = L.marker(intersection.coords, {
            icon,
            draggable: mapControl.editMode
        })

        const time = intersection.time
        if (mapControl.editMode) {
            intersectionMarker.bindPopup(`
                <p>${time}</p>
                <p>Delete Intersection</p>
                <button
                    onclick='mapControl.addModification({
                        type: "deleteIntersection",
                        id: "${time}"
                    })'>
                    Delete
                </button>
            `)
            intersectionMarker.on('dragend', (e) => {
                newCoords = e.target.getLatLng()
                newCoords = `${newCoords.lat},${newCoords.lng}`
                mapControl.addModification({
                    type: "moveIntersection",
                    id: time,
                    coords: newCoords
                })
            })
        } else {
            intersectionMarker.bindPopup(`
                <h4 style="
                    text-align: center;
                    font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif;">
                    ${intersection.numPaths} paths intersect here
                </h4>
            `)
        }
        
        intersectionMarker.addTo(map);

        mapControl.addIntersection(intersectionMarker)
    }
}

if (typeof onMobile !== "undefined") {
    ready()
}
