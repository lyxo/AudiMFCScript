import datetime

class ConsoleLineData:
    
    def __init__(self, text_touples:list(), extra:str=None):    
        self.text_touples:list() = text_touples
        self.extra:str = extra

def generate_text_touples(cars:dict, last_update:str, search_strings:list=['']) -> list:
    """Print the the overview of selected models, all models if None selected, clears the screen beforehand if desired"""
    ret_lines_touples = list()

    str_last_update = '-'
    if last_update:
        str_last_update = last_update.strftime("%H:%M:%S")
    
    # Sort the dictionary before displaying it
    # TODO: allow other sorting
    cars_view = dict(
        sorted(cars.items(), key=lambda item: item[1]["web_data"]["productInfo"]["productName"])
    )

    time_now = datetime.datetime.now()
    max_time_diff = 30
    info_types = ["time_added", "time_changed", "time_removed"]

    # TODO: Handle None String? e.g. as default arg
    # View cars that fit to the searchstring
    evaluated_keys = list()
    for search_string in search_strings:
        search_condition = lambda car_touple : search_string in car_touple[1]["web_data"]["productInfo"]["productName"]

        for car_key, car in filter(search_condition, cars_view.items()):
            if car_key in evaluated_keys:
                continue
            
            # Create a sorted list of metadata changes
            infos_sorted = []
            for info_type in info_types:
                for time_entry in car["meta_data"][info_type]:
                    time_diff = time_now - datetime.datetime.fromtimestamp(time_entry)
                    minutes, seconds = divmod(time_diff.seconds, 60)
                    if minutes <= max_time_diff:
                        infos_sorted.append((minutes, info_type.split("_")[1]))
            infos_sorted = sorted(infos_sorted, key=lambda minutes: infos_sorted[0])

            # Ignore cars that are unavailable and had no updates in max_timediff
            if car["meta_data"]["available"] == False and len(infos_sorted) == 0:
                continue

            info_string = ""

            # Cut sorted list to a maximum of values
            max_infos = 3
            if len(infos_sorted) > max_infos:
                infos_sorted = infos_sorted[:max_infos]
                info_string += "..., "

            # Create the info string
            for info in infos_sorted:
                info_string += f'{info[1]} {info[0]} minutes ago, '
            
            # Remove the last ','
            if len(info_string) > 0 and info_string.endswith(', '):
                info_string = info_string[:-2]

            # Color info string
            line_touples = list()
            name = car["web_data"]["productInfo"]["productName"]
            price = car["web_data"]['price']['priceWithTax'] / 100.0
            if car["meta_data"]["available"]:
                if len(infos_sorted) > 0:
                    line_touples.append((f'{name} ({price}€)', None))
                    line_touples.append((f' ({info_string})\n', colors.OKGREEN))
                else:
                    line_touples.append((f'{name} ({price}€)\n', None))
            else:
                #striked = strike((f'{name} ({price}€)'))
                striked = f'{name} ({price}€)'
                line_touples.append((f'{striked}', colors.GREY))
                line_touples.append((f' ({info_string})\n', colors.GREY))
            
            ret_lines_touples.append(ConsoleLineData(line_touples, car['web_data']['attributes']['CarID']))

    return ret_lines_touples

def generate_error_touples(ex):
    touples = list()
    #touples.append(('An exception has occured:\n', colors.FAIL))
    touples.append(ConsoleLineData([('An exception has occured:\n', colors.FAIL),(str(ex),None)]))
    #touples.append((str(ex),None))
    return touples

class colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    GREY = "\033[90m"

def strike(text):
    return '\u0336'.join(text) + '\u0336'
