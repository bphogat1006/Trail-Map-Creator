drawingProperties = {
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
        weight: 3
    },
    "_other": {
        color: "#000000",
        weight: 4
    }
}

class MapControl {
    constructor() {
        this.baseLayers = {}
        this.trailLayers = {}
        this.pois = L.layerGroup()
        this.layerControl = null
        this.editMode = false
        this.modifications = []
    }

    addBaseLayer(name, layer) {
        this.baseLayers[name] = layer
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

    getOverlays() {
        var overlays = this.trailLayers
        overlays["POI"] = this.pois
        return overlays
    }

    finalize() {
        if (this.layerControl === null) {
            this.layerControl = L.control.layers(this.baseLayers, this.getOverlays())
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
        this.baseLayers = {}
        this.trailLayers = {}
        this.pois = L.layerGroup()
        this.layerControl = null
    }

    enableEditMode() {
        $("#editMode").hide("fast")
        $("#editModeMessage").delay(200).show("fast").delay(3000).hide("fast");
        this.reset()
        this.editMode = true
    }

    addModification(modification) {
        this.modifications.push(modification)
        $("#commitModifications").show("slow")
    }

    commitChanges() {
        $("#commitModifications").hide("slow")
        debug("Make changes to coords.txt and refresh")
        parseDataFile().then(data => {
            for (var modification of this.modifications) {
                
                switch (modification.type) {
                    
                    // Modify coords

                    case "moveCoords":
                        for (i=0; i < data.length; i++) {
                            if (data[i].header === "COORDS" && data[i].time === modification.id) {
                                data[i].coords = modification.coords
                                console.log("Changed", data[i])
                                break
                            }
                        }
                        if (i === data.length) throw `Modification failed: ${modification}`
                        break;
                        
                    case "deleteCoords":
                        
                        break;
                        
                    // Modify trails

                    case "splitTrail":
                        
                        break;

                    case "deleteTrail":
                        
                        break;
                        
                    case "joinTrail":
                        
                        break;
                        
                    // Modify POIs
                    
                    case "movePoi":
                        
                        break;
                        
                    case "deletePoi":
                        
                        break;
                        
                    case "changePoiLink":
                        
                        break;
                
                    default:
                        throw 'modification type not recognized'
                }
            }

            var dataString = ""
            for (obj of data) {
                dataString += "\n"
                switch (obj.header) {
                    case "START":
                        
                        break;
                
                    case "COORDS":
                        
                        break;
                
                    case "POI":
                        
                        break;
                
                    default:
                        break;
                }
            }

            console.log(dataString)
            navigator.clipboard.writeText(dataString)
        })
    }
}

class Park {
    constructor() {
        this.trailCollection = {}
        this.pois = []
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

    getPois() {
        return this.pois
    }
}

async function parseDataFile(parkData=null, getParkNamesOnly=false) {
    function parseData(response) {
        data = []
        i=0
        while (i < response.length) {
            line = String(response[i]).replace(/(\r\n|\n|\r)/gm, "")
            if (line != "") {
                header = line.split(" ")[0]
                contentIndex = header.length+1
                content = line.substring(contentIndex).split(" - ")
                data.push({header, content})
            }
            i++
        }
        returnData = []
        if (getParkNamesOnly) {
            for (obj of data) {
                if (obj.header == "START") {
                    park = obj.content[0]
                    if (!returnData.includes(park)) {
                        returnData.push(park)
                    }
                }
            }
        } else {
            i=0
            while (i < data.length) {
                switch (data[i].header) {
                    case "START":
                        startData = data[i].content
                        returnData.push({
                            header: "START",
                            park: startData[0],
                            trailType: startData[1],
                            time: startData[2]
                        })
                        i+=1
                        break
                    case "TIME":
                        if (data[i+1].header === "COORDS") {
                            coords = data[i+1].content[0].split(',')
                            coords = [parseFloat(coords[0]), parseFloat(coords[1])]
                            returnData.push({
                                header: "COORDS",
                                time: data[i].content[0],
                                coords,
                                accuracy: parseFloat(data[i+2].content[0])
                            })
                            i+=3
                        }
                        else if (data[i+1].header === "POI") {
                            coords = data[i+2].content[0].split(',')
                            coords = [parseFloat(coords[0]), parseFloat(coords[1])]
                            returnData.push({
                                header: "POI",
                                park: data[i+1].content[0],
                                description: data[i+1].content[1],
                                time: data[i].content[0],
                                coords,
                                accuracy: parseFloat(data[i+3].content[0]),
                                imgId: data[i+4].content[0],
                            })
                            i+=5
                        }
                        else {
                            throw "error while parsing park data file"
                        }
                        break
                    default:
                        throw "error while parsing park data file"
                }
            }
        }

        return new Promise((resolve) => {
            // console.log(returnData)
            resolve(returnData)
        })
    }

    if (parkData === null) {
        return fetch("coords.txt")
            .then(response => response.text())
            .then(text => {
                response = String(text).split('\n')
                return parseData(response)
            });
    } else {
        return parseData(parkData)
    }
}