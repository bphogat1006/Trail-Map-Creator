class Park {
    constructor() {
        this.trailCollection = {}
        this.pois = []
        this.intersections = []
    }

    addTrail(trail, trailType) { // trail: array of COORDS objects. trailType: string
        if (!(trailType in this.trailCollection)) {
            this.trailCollection[trailType] = []
        }
        this.trailCollection[trailType].push(trail)
    }

    getTrails(trailType=null) {
        if (trailType===null) return this.trailCollection
        return this.trailCollection[trailType]
    }

    addPoi(poi) {
        this.pois.push(poi)
    }

    addIntersection(intersection) {
        this.intersections.push(intersection)
    }
}

class MapControl {
    drawingProperties = {
        trail: {
            "Paved": {
                color: "#474245",
                weight: 8
            },
            "Gravel": {
                color: "#ADA197",
                weight: 7
            },
            "Dirt": {
                color: "#6D4830",
                weight: 6
            },
            "Off Trail": {
                color: "#A8896D",
                weight: 4
            },
            "Brush": {
                color: "#00B200",
                weight: 4
            },
            "Deer Path": {
                color: "#2A662A",
                weight: 2
            },
            "undefined": {
                color: "#000000",
                weight: 4
            }
        },
        opacity: {
            coords: {
                marker: 0.6,
                accuracy: 0.3
            },
            trail: 1,
            poi: {
                img: 0.75,
                accuracy: 0.1
            }
        }
    }

    constructor() {
        this.trailLayers = {}
        this.pois = L.layerGroup()
        this.intersections = L.layerGroup()
        this.layerControl = null
        this.editMode = false
        this.modifications = []
    }

    addTrail(trail, trailType) {
        if (!(trailType in this.trailLayers)) {
            this.trailLayers[trailType] = L.layerGroup()
        }
        this.trailLayers[trailType].addLayer(trail)
    }

    addPoi(poi) {
        this.pois.addLayer(poi)
    }

    addIntersection(intersection) {
        this.intersections.addLayer(intersection)
    }

    getOverlays() {
        var overlays = this.trailLayers
        overlays["POIs"] = this.pois
        overlays["Intersections"] = this.intersections
        return overlays
    }

    finalize() {
        if (this.layerControl === null) {
            this.layerControl = L.control.layers(null, this.getOverlays())
        } else {
            throw 'something went wrong in mapControl.finalize()'
        }
        for (var [name, layerGroup] of Object.entries(this.getOverlays())) {
            layerGroup.addTo(map)
        }
        this.layerControl.addTo(map)
    }

    reset() {
        $("#selectPark").val("null")
        for (var [name, layerGroup] of Object.entries(this.getOverlays())) {
            map.removeLayer(layerGroup)
        }
        if (this.layerControl != null) {
            this.layerControl.remove(map)
        }
        this.trailLayers = {}
        this.pois = L.layerGroup()
        this.intersections = L.layerGroup()
        this.layerControl = null
        this.modifications = []
    }

    enableEditMode() {
        $("#editMode").hide("fast")
        $("#editModeMessage").delay(200).show("fast").delay(1500).hide("fast");
        this.reset()
        this.editMode = true
    }

    addModification(modification) {
        this.modifications.push(modification)
        $("#commitModifications").show("slow")
        console.log(modification)
    }

    commitChanges() {
        parseDataFile(null, null, false, true).then(allData => {
            var data = allData[$("#selectPark").val()]

            for (var modification of this.modifications) {
                
                switch (modification.type) {
                    
                    // Modify coords

                    case "moveCoords":
                        for (obj of data) {
                            if (obj.header === "COORDS" && obj.time === modification.id) {
                                obj.coords = modification.coords
                                break
                            }
                        }
                        break;
                        
                    case "deleteCoords":
                        for (var i=0; i < data.length; i++) {
                            if (data[i].header === "COORDS" && data[i].time === modification.id) {
                                data.splice(i, 1)
                                break
                            }
                        }
                        break;
                        
                    // Modify POIs
                    
                    case "movePoi":
                        for (obj of data) {
                            if (obj.header === "POI" && obj.time === modification.id) {
                                obj.coords = modification.coords
                                break
                            }
                        }
                        break;
                        
                    case "deletePoi":
                        for (var i=0; i < data.length; i++) {
                            if (data[i].header === "POI" && data[i].time === modification.id) {
                                data.splice(i, 1)
                                break
                            }
                        }
                        break;
                        
                    case "changePoiLink":
                        for (obj of data) {
                            if (obj.header === "POI" && obj.time === modification.id) {
                                obj.imgId = modification.imgId
                                break
                            }
                        }
                        break;
                        
                    // Modify trails

                    case "splitTrail":
                        for (var i=0; i < data.length; i++) {
                            if (data[i].header === "COORDS" && data[i].time === modification.id) {
                                data.splice(i, 0, {
                                    header: "START",
                                    trailType: "Carpet",
                                    time: data[i].time
                                })
                                break
                            }
                        }
                        break;

                    case "deleteTrail":
                        var startIndex = null
                        for (var i=0; i < data.length; i++) {
                            if (data[i].header === "START") {
                                startIndex = i
                            }
                            else if (data[i].header === "COORDS" && data[i].time === modification.id) {
                                break
                            }
                        }
                        data.splice(startIndex, 1)
                        while (startIndex < data.length && data[startIndex].header === "COORDS") {
                            data.splice(startIndex, 1)
                        }
                        break;
                        
                    case "joinTrail":
                        
                        break;
                        
                    case "reverseTrail":
                        
                        break;

                    // Modify intersections
                    
                    case "moveIntersection":
                        for (obj of data) {
                            if (obj.header === "INTERSECTION" && obj.time === modification.id) {
                                obj.coords = modification.coords
                                break
                            }
                        }
                        break;
                        
                    case "deleteIntersection":
                        for (var i=0; i < data.length; i++) {
                            if (data[i].header === "INTERSECTION" && data[i].time === modification.id) {
                                data.splice(i, 1)
                                break
                            }
                        }
                        break;
                
                    default:
                        throw 'Modification type not recognized: '+modification
                }
            }

            // saving and copying changes
            allData[$("#selectPark").val()] = data
            navigator.clipboard.writeText(JSON.stringify(allData))
            this.modifications = []
            $("#commitModifications").hide("slow")
            debug("Changes copied. Paste changes to coords.txt and refresh")
        })
    }
}

async function parseDataFile(parkData=null, selectedPark, getParkNamesOnly=false, getAllData=false) {
    function parseData(data) {
        return new Promise((resolve) => {
            result = null
            json = JSON.parse(data)
            if (getAllData) {
                resolve(json)
            } else {
                if (getParkNamesOnly) {
                    result = Object.keys(json)
                } else {
                    for (obj of json[selectedPark]) {
                        if (obj.header === "COORDS" || obj.header === "POI" || obj.header === "INTERSECTION") {
                            obj.accuracy = parseFloat(obj.accuracy)
                            obj.coords = obj.coords.split(",")
                            obj.coords = [parseFloat(obj.coords[0]),parseFloat(obj.coords[1])]
                        }
                    }
                    result = json[selectedPark]
                }
                // console.log(result)
                resolve(result)
            }
        })
    }

    if (parkData === null) {
        return fetch("coords.txt")
            .then(response => response.text())
            .then(text => {
                return parseData(text)
            });
    } else {
        return parseData(parkData)
    }
}