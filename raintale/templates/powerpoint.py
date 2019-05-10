import logging

from pptx import Presentation
from jinja2 import Template

from .storyteller import FileStoryteller, get_story_elements, split_multipart_template
from ..surrogatedata import get_memento_data, get_template_surrogate_fields, datauri_to_data

module_logger = logging.getLogger('raintale.storytellers.powerpoint')

class PowerpointStoryteller(FileStoryteller):

    description = "Given input data and a template file, this storyteller generates a Powerpoint presentation based on the template."

    def generate_story(self, story_data, mementoembed_api, story_template):
        
        title_template, element_template, media_template_list = split_multipart_template(story_template)

        story_elements = get_story_elements(story_data)

        module_logger.debug("media_template_list: {}".format(media_template_list))
        
        story_output_data = {
            "main_tweet": "",
            "thread_tweets": []
        }

        story_output_data["main_tweet"] = Template(title_template).render(
                title=story_data['title'],
                generated_by=story_data['generated_by'],
                collection_url=story_data['collection_url']
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
                                surrogate=field_data
                        ))

                    module_logger.debug("media_uris: {}".format(media_uris))

                    story_output_data["thread_tweets"].append(
                        {
                            "text": Template(element_template).render(
                                surrogate=memento_data
                            ),
                            "media": media_uris
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

        return story_output_data

    def publish_story(self, story_output_data):

        module_logger.info("writing story to Powerpoint file named {}".format(self.output_filename))

        # with open(self.output_filename, 'w') as f:
        #     f.write(story_output_data)

        # 0. record starting directory
        # 1. make a temporary directory
        
        # 2. save file there
        prs = Presentation()
        prs.save("mystory.pptx")
        # 3. Unzip file
        # zip_ref = zipfile.ZipFile(temporary_file)
        # zip_ref.extractall('.')
        # zip_ref.close()
        # 4. go into ppt/slides directory
        # os.chdir("{}/ppt/slides".format(temporary_directory))
        # 5. create file slide1.xml
        # 6. write out data for title slide
        # with open("slide1.xml", 'w') as f:
        #   f.write(story_output_data["main_slide"])

        threadslidecounter = 2
        threadslidecount = len(story_output_data["thread_slides"])

        for thread_slide in story_output_data["thread_slides"]:
            # 7. open next slide
            # 8. write out data for element slide
            with open("slide{}.xml".format(threadslidecounter), 'w') as f:
                f.write(thread_slide["text"])

            threadtweetcounter += 1

        # 9. change back up to top directory
        # 10. delete temporary file
        # 11. zip everything else back up into a pptx file
        # 12. change back to starting directory
        

        module_logger.info(
            "Your story has been told to file {}".format(
                self.output_filename
            )
        )
