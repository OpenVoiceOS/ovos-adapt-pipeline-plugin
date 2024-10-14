# Copyright 2018 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__author__ = 'seanfitz'

from ovos_workshop.intent import Intent, IntentBuilder


def is_entity(tag, entity_name):
    for entity in tag.get('entities'):
        for v, t in entity.get('data'):
            if t.lower() == entity_name.lower():
                return True
    return False


def find_first_tag(tags, entity_type, after_index=-1):
    """Searches tags for entity type after given index

    Args:
        tags(list): a list of tags with entity types to be compared to
         entity_type
        entity_type(str): This is he entity type to be looking for in tags
        after_index(int): the start token must be greater than this.

    Returns:
        ( tag, v, confidence ):
            tag(str): is the tag that matched
            v(str): ? the word that matched?
            confidence(float): is a measure of accuracy.  1 is full confidence
                and 0 is none.
    """
    return Intent._find_first_tag(tags, entity_type, after_index)


def find_next_tag(tags, end_index=0):
    for tag in tags:
        if tag.get('start_token') > end_index:
            return tag
    return None


def choose_1_from_each(lists):
    """
    The original implementation here was functionally equivalent to
    :func:`~itertools.product`, except that the former returns a generator
    of lists, and itertools returns a generator of tuples. This is going to do
    a light transform for now, until callers can be verified to work with
    tuples.

    Args:
        A list of lists or tuples, expected as input to
        :func:`~itertools.product`

    Returns:
        a generator of lists, see docs on :func:`~itertools.product`
    """
    return Intent._choose_1_from_each(lists)


def resolve_one_of(tags, at_least_one):
    """Search through all combinations of at_least_one rules to find a
    combination that is covered by tags

    Args:
        tags(list): List of tags with Entities to search for Entities
        at_least_one(list): List of Entities to find in tags

    Returns:
        object:
        returns None if no match is found but returns any match as an object
    """
    return Intent._resolve_one_of(tags, at_least_one)

