import logging
import sys # for debugging
import pprint # for debugging

from yaml import load, Loader
from jinja2 import Template

from ..surrogatedata import get_memento_data, get_template_surrogate_fields

module_logger = logging.getLogger('raintale.storytellers.storyteller')

class StoryTellerException(Exception):
    pass

class StoryTellerCredentialParseError(StoryTellerException):
    pass

class StoryTellerStoryParseError(StoryTellerException):
    pass

class StoryTellerMultipartTemplateParseError(StoryTellerException):
    pass

def get_story_elements(story_data):

    try:
        story_elements = story_data['elements']
        return story_elements
    except KeyError:
        msg = "Cannot tell story. Story does not contain elements. "
        module_logger.exception(msg)
        raise StoryTellerStoryParseError(msg)

def split_multipart_template(template_contents):

    if template_contents[0:34] != '{# RAINTALE MULTIPART TEMPLATE #}\n':
        msg = "Multipart Template required, but not submitted, cannot continue..."
        module_logger.critical(msg)
        raise StoryTellerMultipartTemplateParseError(msg)

    template_contents = template_contents[34:]

    if template_contents[0:26] != '{# RAINTALE TITLE PART #}\n':
        msg = "Raintale Title Part required in Multipart Template, but not present, cannot continue..."
        module_logger.critical(msg)
        raise StoryTellerMultipartTemplateParseError(msg)

    template_contents = template_contents[26:]

    try:
        title_template, element_template = template_contents.split('{# RAINTALE ELEMENT PART #}\n')
    except ValueError:
        msg = "Raintale Element Part required in Multipart Template, but not present, cannot continue..."
        module_logger.critical(msg)
        raise StoryTellerMultipartTemplateParseError(msg)

    try:
        element_template, media_template = element_template.split('{# RAINTALE ELEMENT MEDIA #}')
        media_list = media_template.split('\n')
        
        # TODO: this should not be necessary
        cleaned_media_list = []
        module_logger.debug("media_list: {}".format(media_list))

        for item in media_list:

            if item != '':
                cleaned_media_list.append(item)

        module_logger.debug("cleaned_media_list: {}".format(cleaned_media_list))

    except ValueError:
        media_list = []

    return title_template, element_template, cleaned_media_list

class Storyteller:

    description = "ERROR"

    def generate_story(self, story_data, mementoembed_api, story_template):
        raise NotImplementedError(
            "StoryTeller class is not meant to be called directly. "
            "Create a child class to use StoryTeller functionality.")

    def publish_story(self, story_output_data):
        raise NotImplementedError(
            "StoryTeller class is not meant to be called directly. "
            "Create a child class to use StoryTeller functionality.")

    def tell_story(self, story_data, mementoembed_api, story_template):

        story_output_data = self.generate_story(story_data, mementoembed_api, story_template)
        self.publish_story(story_output_data)

class ServiceStoryteller(Storyteller):

    requires_file = False
    requires_credentials = True

    def __init__(self, credentials_filename):
        self.credentials_filename = credentials_filename
        self.load_credentials_filename()
        self.auth()

    def load_credentials_filename(self):

        with open(self.credentials_filename) as f:
            self.credentials = load(f, Loader=Loader)

    def generate_story(self, story_data, mementoembed_api, story_template):

        title_template, element_template, media_template_list = split_multipart_template(story_template)

        story_elements = get_story_elements(story_data)

        module_logger.debug("media_template_list: {}".format(media_template_list))
        
        story_output_data = {
            "main_post": "",
            "comment_posts": []
        }

        story_output_data["main_post"] = Template(title_template).render(
                title=story_data['title'],
                generated_by=story_data['generated_by'],
                collection_url=story_data['collection_url'],
                metadata=story_data['metadata']
        )

        template_surrogate_fields = get_template_surrogate_fields(element_template)

        template_media_fields = []
        
        for field in media_template_list:

            # there should only be one
            template_media_fields.append(
                get_template_surrogate_fields(field)[0]
            )

        module_logger.debug("template_media_fields: {}".format(template_media_fields))

        module_logger.info("preparing to iterate through {} story "
            "elements".format(len(story_elements)))

        for element in story_elements:

            module_logger.debug("working on story element {}".format(element))

            try:

                if element['type'] == 'link':

                    urim = element['value']

                    memento_data = get_memento_data(
                        template_surrogate_fields, 
                        mementoembed_api, 
                        urim)

                    module_logger.debug("memento_data: {}".format(memento_data))

                    media_uris = []

                    module_logger.debug("template_media_fields: {}".format(template_media_fields))

                    for field in template_media_fields:

                        module_logger.debug("field: {}".format(field))
                        field_data = get_memento_data(
                            [field],
                            mementoembed_api,
                            urim
                        )
                        media_uris.append(
                                Template(field).render(
                                element={
                                    "surrogate": field_data
                                }
                        ))

                    module_logger.debug("media_uris: {}".format(media_uris))

                    story_output_data["comment_posts"].append(
                        {
                            "text": Template(element_template).render(
                                {
                                    "element": {
                                        "surrogate": memento_data
                                    }
                                }
                            ),
                            "media": media_uris
                        }
                    )

                elif element['type'] == 'text':

                    story_output_data["comment_posts"].append(
                        {
                            "text": element['value'],
                            "media": []
                        }
                    )

                else:
                    module_logger.warning(
                        "element of type {} is unsupported, skipping...".format(element['type'])
                    )

            except KeyError:

                module_logger.exception(
                    "cannot process story element data of {}, skipping".format(element)
                )

        module_logger.debug(
            "story_output_data: {}".format(pprint.pformat(story_output_data))
        )

        return story_output_data

    def auth(self):
        raise NotImplementedError(
            "ServiceStoryTeller class is not meant to be called directly. "
            "Create a child class to use ServiceStoryTeller functionality.")

    def reset_credentials(self, credentials):
        raise NotImplementedError(
            "ServiceStoryTeller class is not meant to be called directly. "
            "Create a child class to use ServiceStoryTeller functionality.")

class FileStoryteller(Storyteller):

    requires_file = True
    requires_credentials = False

    def __init__(self, output_filename):
        self.output_filename = output_filename
        module_logger.info("output filename set to {}".format(self.output_filename))

    def reset_output_filename(self, output_filename):
        self.output_filename = output_filename


