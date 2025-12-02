list1 = [1, 2, 3]
list2 = list1
list2.append(4)

print(list1) # [1, 2, 3, 4]
print(list2) # [1, 2, 3, 4]

list3 = [1, 2, 3]
list4 = list3.copy()
list4.append(4)

print(list3) # [1, 2, 3]
print(list4) # [1, 2, 3, 4]



def add_item(my_list, item):
    my_list.append(item)
    return my_list

original = [1, 2, 3]
result = add_item(original, 4)

print(original) # [1, 2, 3, 4]
print(result)   # [1, 2, 3, 4]
print(original is result) # True


def add_item_safe(my_list, item):
    new_list = my_list.copy()
    new_list.append(item)
    return new_list

original2 = [1, 2, 3]
result2 = add_item_safe(original2, 4)

print(original2)  # [1, 2, 3]
print(result2)    # [1, 2, 3, 4]

""" 
Experiments 1 and 3 behave the way they do because when you do this:
list2 = list1, you are referencing or linking the lists together not copying the values of one list to the other. So when you append list2, you also append list1 
"""
