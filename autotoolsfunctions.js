/**
* These functions will automatically be injected into every page that is loaded with the AutoTools Web Screen action in Tasker.
* You can use them freely in your own web screens! :)
* If you want you can copy these to your web screen for easy testing on your PC.
* Only the functions that call AutoToolsAndroid functions will not work on your PC, like the AutoTools.say function for example.
*/

/**
 * Create base AutoTools object that will contain everything else
 */
var AutoTools = {};

/**
 * Send an AutoApps command from JavaScript.
 * @param {string} command - The command you want to send
 * @param {string} [prefix] - An optional prefix that will be prepended to the command. If it exists command will have the prefix=:=command format
 * @param {boolean} [hapticFeedback] - If true, will perform a short vibration with the command
 */
AutoTools.sendCommand = function(command, prefix, hapticFeedback){
    if(!command){
        return;
    }
    if(!prefix){
        prefix = null;
    }
    console.log("Sending command: " + command+";"+prefix);
    AutoToolsAndroid.sendCommand(command, prefix, hapticFeedback);
}

/**
 * Easily assign a command to an HTML element
 * @param {string} selector - The CSS selector for the element. For example, to specify an element with the id "link", you should pass in "#link"
 * @param {string} command - The command you want to send
 * @param {string} [prefix] - An optional prefix that will be prepended to the command. If it exists command will have the prefix=:=command format
 */
AutoTools.commandOnClick = function(selector, command, prefix){
    document.querySelector(selector).onclick = e => AutoTools.sendCommand(command, prefix);
}
/**
 * Change a color dynamically. Got it from here: https://stackoverflow.com/questions/5560248/programmatically-lighten-or-darken-a-hex-color-or-rgb-and-blend-colors
 * Example use: Have color #ff0000 (red) and want a 30% darker shade of red, would call AutoTools.shadeBlendConvert(-0.3, "#ff0000");
 */
AutoTools.shadeBlendConvert = function(p, from, to) {
    if(typeof(p)!="number"||p<-1||p>1||typeof(from)!="string"||(from[0]!='r'&&from[0]!='#')||(typeof(to)!="string"&&typeof(to)!="undefined"))return null;
    var sbcRip=function(d){
        var l=d.length,RGB=new Object();
        if(l>9){
            d=d.split(",");
            if(d.length<3||d.length>4)return null;
            RGB[0]=i(d[0].slice(4)),RGB[1]=i(d[1]),RGB[2]=i(d[2]),RGB[3]=d[3]?parseFloat(d[3]):-1;
        }else{
            if(l==8||l==6||l<4)return null;
            if(l<6)d="#"+d[1]+d[1]+d[2]+d[2]+d[3]+d[3]+(l>4?d[4]+""+d[4]:"");
            d=i(d.slice(1),16),RGB[0]=d>>16&255,RGB[1]=d>>8&255,RGB[2]=d&255,RGB[3]=l==9||l==5?r(((d>>24&255)/255)*10000)/10000:-1;
        }
        return RGB;}
    var i=parseInt,r=Math.round,h=from.length>9,h=typeof(to)=="string"?to.length>9?true:to=="c"?!h:false:h,b=p<0,p=b?p*-1:p,to=to&&to!="c"?to:b?"#000000":"#FFFFFF",f=sbcRip(from),t=sbcRip(to);
    if(!f||!t)return null;
    if(h)return "rgb("+r((t[0]-f[0])*p+f[0])+","+r((t[1]-f[1])*p+f[1])+","+r((t[2]-f[2])*p+f[2])+(f[3]<0&&t[3]<0?")":","+(f[3]>-1&&t[3]>-1?r(((t[3]-f[3])*p+f[3])*10000)/10000:t[3]<0?f[3]:t[3])+")");
    else return "#"+(0x100000000+(f[3]>-1&&t[3]>-1?r(((t[3]-f[3])*p+f[3])*255):t[3]>-1?r(t[3]*255):f[3]>-1?r(f[3]*255):255)*0x1000000+r((t[0]-f[0])*p+f[0])*0x10000+r((t[1]-f[1])*p+f[1])*0x100+r((t[2]-f[2])*p+f[2])).toString(16).slice(f[3]>-1||t[3]>-1?1:3);
};

/**
 * Brighten the color of a property in a CSS rule
 * @param {Object} rule - The cssRule object you want to change
 * @param {string} propertyName - The property you want to change ("background-color" for example)
 * @param {string} percent - Value from 0 to 100 you want to change
 * @param {boolean} darken - If true will darken the color instead of brightening it
 */
AutoTools.increaseBrightnessRule = function(rule, propertyName, percent, darken){
    var originalColor = rule.style.getPropertyValue(propertyName);
    if(!originalColor){
        return;
    }
    originalColor = originalColor.trim();
    var newColor = AutoTools.shadeBlendConvert(percent/100,originalColor);
    rule.style.setProperty(propertyName, newColor);
    return newColor;
};

/**
 * Check if the value of a Web Screen Variable was set from Tasker
 * @param {string} value - Name of the variable you want to check
 */
AutoTools.isSet = value => {
    value = window[value];
    if(value === undefined || value === null){
        return false;
    }
    var toClass = {}.toString.call(value);
    if(toClass  == "[object Boolean]"){
        return true;
    }
    return toClass  == "[object String]";
};
/**
 * Set the value of a Web Screen variable if it hasn't been set already from Tasker
 * @param {string} variable - The name of the variable you want to set
 * @param {string} value - The value you want to set if it hasn't been set from Tasker
 */
AutoTools.setDefault = (variable, value) => {
    if(!AutoTools.isSet(variable)){
        window[variable] = value;
    }
};
/**
 * As above but for setting multiple values
 * @param {Object} values - Object to set default values of.
 * For example, using
 * AutoTools.setDefault("title","My Title");
 * AutoTools.setDefault("text","my text");
 * Is the same as using
 * AutoTools.setDefaultValues({
    "title": "My Title",
    "text":"my text"
   });
 */
AutoTools.setDefaultValues = (values) => {
    for(var varName in values){
        var value = values[varName];
        AutoTools.setDefault(varName, value);
    }
};

/**
 * Will convert a list of comma separated Web Screen variables into a nice JSON object.
 * @param {...string} fields - Names of the Web Screen Variables to convert
 * For example if have
 * - variable "title" with value = "Title1,Title2,Title3"
 * - variable "text" with value = "text1,text2,text3"
 * And use
 * AutoTools.fieldsToObject("title","text");
 * It'll return an array of objects like this:
[
    {
        "title": "Title1",
        "text": "Text1"
    },
    {
        "title": "Title2",
        "text": "text2"
    },
    {
        "title": "Title3",
        "text": "text3"
    }
]
 * This is much easier to use in JavaScript :)
 */
AutoTools.fieldsToObject = (...fields) => {
    var first =  fields[0];
    var result = [];
    /*if(!AutoTools.isSet(first)){
        return result;
    }*/
    var length = null;
    var separator = ",";
    if(AutoTools.isSet("itemSeparator")){
        separator =  itemSeparator;
    }
    for(var field of fields){
        if(!AutoTools.isSet(field)){
            continue;
        }
        var value = window[field];
        var split = value.split(separator);
        if(length == null){
            length = split.length;
        }
        for (var i = 0; i < length; i++) {
            if(result.length<=i){
                result.push({});
            }
            var current = result[i];
            current[field] = split[i];
        }
    }
    return result;
};

/**
 * Will hide an element on the page
 * @param {HTMLElement} element - The element you want to hide
*/
AutoTools.hide = element => element.classList.add("hidden");

/**
 * Will show an element on the page
 * @param {HTMLElement} element - The element you want to show
*/
AutoTools.show = element => element.classList.remove("hidden");

/**
 * Will convert an array object into HTML elements on the page. It will map each property in the object with elements with the same class name. Check this page for a concrete example: https://www.dropbox.com/s/ia2m4quij24h13q/functiondemo.html?dl=1
 * @param {string} rootElementsId - The ID of the HTML element where you want to insert the HTML elements
 * @param {string} rootElementClass - The class of the HTML element that you want to clone for each item in the input array
 * @param {Object[]} input - The array that contains properties that will be mapped to each replicated HTML element
 * @param {Function} [itemTransformer] - Optional transformer that will be called for each element on the page
*/
AutoTools.objectToElements = function(rootElementsId, rootElementClass, input, itemTransformer){
    var setByClass = (root,className,value,prop) => {
        var element = root.querySelector(`.${className}`);
        if(!element){
            return;
        }
        if(!value){
            AutoTools.hide(element);
            return element;
        }
        AutoTools.show(element);
        if(!prop){
            var tagName = element.tagName;
            if(tagName == "IMG"){
                prop = "src";
            }else if(tagName == "A"){
                prop = "href";
            }else if(tagName == "INPUT"){
                if(element.type == "checkbox"){
                    prop = "checked";
                    value = value == "false" ? false : true;
                }
            }else{
                prop = "innerHTML";
            }
        }
        element[prop] = value;
        return element;
    };
    var listRoot = document.querySelector("#"+rootElementsId);
    var elementToClone = document.querySelector("."+rootElementClass);
    AutoTools.hide(elementToClone);
    var rootElement = elementToClone.cloneNode(true);
    AutoTools.show(rootElement);
    listRoot.innerHTML = "";
    if(itemTransformer && itemTransformer.onclick){
        var styleNoPointerEvents = document.createElement("style");
        styleNoPointerEvents.innerHTML = `
        .${rootElementClass}{
            cursor: pointer;
        }
        .${rootElementClass} *{
            pointer-events: none;
        }`;
        document.querySelector("head").appendChild(styleNoPointerEvents);
    }
    for(var item of input){

        var resultElement = rootElement.cloneNode(true);
        resultElement.item = item;
        var itemObject = {"parent":resultElement};
        for(var prop in item){
            var value = item[prop];
            var setElement = setByClass(resultElement,prop,value);
            itemObject[prop] = {"value":value,"element":setElement};
        }
        if(itemTransformer){
            if(itemTransformer.item){
                itemTransformer.item(itemObject);
            }
            if(itemTransformer.onclick){
                resultElement.onclick = e => itemTransformer.onclick(e.target.item);
            }
            if(itemTransformer.events){
                for(var event of itemTransformer.events){
                    var eventName = event.name;
                    if(!eventName){
                        continue;
                    }
                    var handler = event.handler;
                    if(!handler){
                        continue;
                    }
                    var cssQuery = event.query;
                    var elementForEvent = resultElement;
                    if(cssQuery){
                        elementForEvent = resultElement.querySelector(cssQuery);
                        if(!elementForEvent){
                            continue;
                        }
                        elementForEvent.style["pointer-events"] = "auto";
                    }
                    elementForEvent.addEventListener(eventName,e => handler(e.target));
                }
            }
        }
        if(itemObject.elementToAdd){
            resultElement = itemObject.elementToAdd;
        }
        if(itemObject.elementRoot){
            listRoot = itemObject.elementRoot;
        }
        listRoot.appendChild(resultElement);
     }
}
/**
 * Will convert Web Screen variables into HTML elements on the page. It will map each variable with elements with the same class name. Check this page for a concrete example: https://www.dropbox.com/s/ia2m4quij24h13q/functiondemo.html?dl=1
 * @param {string[]} webscreenVariables - Array of variable names that you want to map to the HTML element
 * @param {string} rootElementsId - The ID of the HTML element where you want to insert the HTML elements
 * @param {string} rootElementClass - The class of the HTML element that you want to clone for each item in the input array
 * @param {Function} [itemTransformer] - Optional transformer that will be called for each element on the page
 */
AutoTools.variablesToElements = function(webscreenVariables, rootElementsId, rootElementClass, itemTransformer){
        var input = AutoTools.fieldsToObject(...webscreenVariables);
        AutoTools.objectToElements(rootElementsId,rootElementClass, input, itemTransformer);
}
/**
 * Will say some text out loud on your Android device
 * @param {string} text - Text you want to say
 * @param {string} [language] - Optional language. Will default to your device's language
 */
AutoTools.say = (text,language) => AutoToolsAndroid.say(text,language);
/**
 * Will return info about the user that's logged in to AutoTools (usually you). Try it here with the "userId" set to "me" to see what kind of output you get: https://developers.google.com/+/web/api/rest/latest/people/get
 */
AutoTools.getUserInfo = () => JSON.parse(AutoToolsAndroid.getUserInfo());
/**
 * Will make your phone vibrate with the given vibration pattern.
 * @param {string} vibration - Vibration Pattern. Same as Tasker's vibrate pattern
 */
AutoTools.vibrate = (vibration) => AutoToolsAndroid.vibrate(vibration);
/**
 * Will make your phone vibrate shortly
 */
AutoTools.hapticFeedback = () => AutoToolsAndroid.hapticFeedback();
/**
 * Will change the width of the Web Screen if it's an overlay or a dialog
 * @param {string} width - in dp or "fill" to fill the entire width of the screen
 */
AutoTools.setWidth = (width) => AutoToolsAndroid.setWidth(width);
/**
 * Will change the height of the Web Screen if it's an overlay or a dialog
 * @param {string} height - in dp or "fill" to fill the entire height of the screen
 */
AutoTools.setHeight = (width) => AutoToolsAndroid.setHeight(width);
/**
 * Will change the size of the Web Screen if it's an overlay or a dialog
 * @param {string} width - in dp or "fill" to fill the entire width of the screen
 * @param {string} height - in dp or "fill" to fill the entire height of the screen
 */
AutoTools.setSize = (width,height) => AutoToolsAndroid.setSize(width,height);

AutoTools.GRAVITY_BOTTOM = 80;
AutoTools.GRAVITY_CENTER = 17;
AutoTools.GRAVITY_TOP = 48;
AutoTools.GRAVITY_RIGHT = 5;
AutoTools.GRAVITY_LEFT = 3;

/**
 * Will change the size of the Web Screen if it's an overlay or a dialog
 * @param {string} width - in dp or "fill" to fill the entire width of the screen
 * @param {string} height - in dp or "fill" to fill the entire height of the screen
 * @param {string} x - offset in dp
 * @param {string} y - offset in dp
 * @param {int} gravity - flag for gravity: combination of any of the GRAVITY flags above
 */
AutoTools.setLayout = (width, height, x, y, gravity) => AutoToolsAndroid.setLayout(width, height, x, y, gravity);

AutoTools.FLAG_NOT_FOCUSABLE = 8;
AutoTools.FLAG_LAYOUT_NO_LIMITS = 512;
AutoTools.FLAG_TURN_SCREEN_ON = 2097152;
AutoTools.FLAG_ALT_FOCUSABLE_IM = 131072;
AutoTools.FLAG_NOT_TOUCH_MODAL = 32;

/**
 * Will set overlay flags manually. Can be used to adjust if web screen requires input at runtime
 * @param {int} flags - flags to set. Check here: https://developer.android.com/reference/android/view/WindowManager.LayoutParams.html
 */
AutoTools.setWindowFlags = (flags) => AutoToolsAndroid.setWindowFlags(flags);

/**
 * Will show a toast with the given text
 * @param {string} text - text to show in the toast
 */
AutoTools.showToast = (text) => AutoToolsAndroid.showToast(text);

/**
 * Will get the Tasker input that was used to show the screen
 */
AutoTools.getInput = () => JSON.parse(AutoToolsAndroid.getInput());

/**
 * Will get the Tasker input that was used to show the screen
 */
AutoTools.getTextInput = (title,message,initialText) => AutoToolsAndroid.getTextInput(title,message,initialText);

/**
 * Will open the URL on your Android device in an external app
 */
AutoTools.browseUrl = url => AutoToolsAndroid.browseUrl(url);

/**
 * Will get the location of the overlay (as an object with two properties: x and y. Like {x:100,y:200}) f the screen is shown in overlay mode. If not, will return null.
 */
AutoTools.getOverlayPosition = () => {
    var point = AutoToolsAndroid.getOverlayPosition();
    if(!point){
        return point;
    }
    return JSON.parse(point);
}

/**
 * Will create a new style element in the header of the page with the contents passed in as parameter
 * @param {string} css - css text to add in a style element
 */
AutoTools.addStyle = (css) => {
    var sheet = document.createElement('style')
    sheet.innerHTML = css;
    document.head.appendChild(sheet);
}

/**
 * Will return the input with the suffix 'px' if it's a number, otherwise will return the input
 * @param {string} dimension - either a number or any other type of dimension
 */
AutoTools.getPixelsOrDimension = (dimension) => {
    if(!isNaN(new Number(dimension))){
        return dimension+"px";
    }
    return dimension;
}

/**
 * Check if a certain flag is set
 * @param {int} flags - flags to check
 * @param {int} flagToCheck - flag to check
 */
AutoTools.checkFlag = (flags, flagToCheck) => {
    if ((flags & flagToCheck) == flagToCheck){
        return true;
    }
    return false;
}


AutoTools.DRAG_LOCK_ALL = "0";
AutoTools.DRAG_LOCK_HORIZONTAL = "1";
AutoTools.DRAG_LOCK_VERTICAL = "2";
AutoTools.DRAG_LOCK_NONE = "3";

/**
 * Enable or disable vertical dragging in overlays
 * @param {boolean} enable - select if you want to enable or disable it
 */
AutoTools.setDragInY = enable => AutoToolsAndroid.setDragInY(enable);

/**
 * Enable or disable horizontal dragging in overlays
 * @param {boolean} enable - select if you want to enable or disable it
 */
AutoTools.setDragInX = enable => AutoToolsAndroid.setDragInX(enable);

AutoTools.FLING_TO_DISMISS_NONE = "0";
AutoTools.FLING_TO_DISMISS_ALL = "1";
AutoTools.FLING_TO_DISMISS_UP = "2";
AutoTools.FLING_TO_DISMISS_RIGHT = "3";
AutoTools.FLING_TO_DISMISS_DOWN = "4";
AutoTools.FLING_TO_DISMISS_LEFT = "5";
AutoTools.FLING_TO_DISMISS_UP_AND_DOWN = "6";
AutoTools.FLING_TO_DISMISS_LEFT_AND_RIGHT = "7";
/**
 * Enable or disable fling to dismiss on negative X
 * @param {boolean} enable - select if you want to enable or disable it
 */
AutoTools.setflingOnNegativeX = enable => AutoToolsAndroid.setflingOnNegativeX(enable);

/**
 * Enable or disable fling to dismiss on positive X
 * @param {boolean} enable - select if you want to enable or disable it
 */
AutoTools.setflingOnPositiveX = enable => AutoToolsAndroid.setflingOnPositiveX(enable);

/**
 * Enable or disable fling to dismiss on negative Y
 * @param {boolean} enable - select if you want to enable or disable it
 */
AutoTools.setflingOnNegativeY = enable => AutoToolsAndroid.setflingOnNegativeY(enable);

/**
 * Enable or disable fling to dismiss on positive Y
 * @param {boolean} enable - select if you want to enable or disable it
 */
AutoTools.setflingOnPositiveY = enable => AutoToolsAndroid.setflingOnPositiveY(enable);

/**
 * Check if fling to dismiss is enabled for left
 * @param {string} fling - current fling to dismiss value
 */
AutoTools.checkFlingLeft = fling => fling == AutoTools.FLING_TO_DISMISS_LEFT || fling == AutoTools.FLING_TO_DISMISS_LEFT_AND_RIGHT || fling == AutoTools.FLING_TO_DISMISS_ALL;
/**
 * Check if fling to dismiss is enabled for right
 * @param {string} fling - current fling to dismiss value
 */
AutoTools.checkFlingRight = fling => fling == AutoTools.FLING_TO_DISMISS_RIGHT || fling == AutoTools.FLING_TO_DISMISS_LEFT_AND_RIGHT || fling == AutoTools.FLING_TO_DISMISS_ALL;
/**
 * Check if fling to dismiss is enabled for up
 * @param {string} fling - current fling to dismiss value
 */
AutoTools.checkFlingUp = fling => fling == AutoTools.FLING_TO_DISMISS_UP || fling == AutoTools.FLING_TO_DISMISS_UP_AND_DOWN || fling == AutoTools.FLING_TO_DISMISS_ALL;
/**
 * Check if fling to dismiss is enabled for down
 * @param {string} fling - current fling to dismiss value
 */
AutoTools.checkFlingDown = fling => fling == AutoTools.FLING_TO_DISMISS_DOWN || fling == AutoTools.FLING_TO_DISMISS_UP_AND_DOWN || fling == AutoTools.FLING_TO_DISMISS_ALL;

/**
 * Sleep for some time. Should be called with the await keyword
 * @param {int} time - ms to wait
 */
AutoTools.sleep = async time => new Promise(resolve=>setTimeout(resolve,time));

/**
 * Add a click and long click listener to a DOM element
 * @param {HTMLElement} element - DOM element to attach listeners to
 * @param {Function} callbackClick - optional function to run when element is clicked
 * @param {Function} callbackLongClick - optional function to run when element is long clicked
 * @param {int} longClickTime - time to wait until a long click is acknowledged
 */
AutoTools.onclickandlongclick = function(element, callbackClick, callbackLongClick,longClickTime){
    var longpress = false;
    var presstimer = null;
    var longtarget = null;
    if(!longClickTime)longClickTime=500;

    var cancel = function(e) {
        if (presstimer !== null) {
            clearTimeout(presstimer);
            presstimer = null;
        }

        this.classList.remove("longpress");
    };

    var click = function(e) {
        if (presstimer !== null) {
            clearTimeout(presstimer);
            presstimer = null;
        }

        this.classList.remove("longpress");

        if (longpress) {
            return false;
        }
        if(callbackClick)callbackClick(e);
    };

    var start = function(e) {

        if (e.type === "click" && e.button !== 0) {
            return;
        }

        longpress = false;

        this.classList.add("longpress");

        presstimer = setTimeout(function() {
            if(callbackLongClick)callbackLongClick(e);
            longpress = true;
        }, longClickTime);

        return false;
    };

    element.addEventListener("mousedown", start);
    element.addEventListener("touchstart", start);
    element.addEventListener("click", click);
    element.addEventListener("mouseout", cancel);
    element.addEventListener("touchend", cancel);
    element.addEventListener("touchleave", cancel);
    element.addEventListener("touchcancel", cancel);
}

