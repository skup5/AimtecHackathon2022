# translates human orders to robot commands

# importing the module
import json

COMMANDS_INPUT_FILE_NAME = 'commands.json'


def read_commands() -> dict:
    # Opening JSON file
    with open(COMMANDS_INPUT_FILE_NAME, encoding='utf8') as json_file:
        return json.load(json_file)


class Commander:
    commands = {}

    def get_commands(self) -> dict:
        if len(self.commands) == 0:
            self.commands = read_commands()

        return self.commands

    def translate_command(self, human_command) -> str:
        actual_commands = self.get_commands()
        for key in actual_commands.keys():
            # print(key+':')
            for human_word in actual_commands[key]:
                # print(human_word)
                if human_word == human_command:
                    return key

        return ''


searched_command = 'dozadu'
print(searched_command + ' -> ' + Commander().translate_command(searched_command))
